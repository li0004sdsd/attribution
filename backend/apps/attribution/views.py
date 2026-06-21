from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import get_user_role, get_allowed_models, ROLE_ADMIN, ROLE_OPERATOR, ROLE_USER
from apps.journeys.models import ConversionPath
from apps.channels.models import AdChannel
from .engine import MODELS
from .models import AttributionResult
from .serializers import AttributionResultSerializer, RunAttributionSerializer


class RunAttributionView(APIView):
    def post(self, request):
        serializer = RunAttributionSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        model_type = serializer.validated_data['model_type']
        allowed = get_allowed_models(request.user)
        if allowed is not None and model_type not in allowed:
            return Response(
                {'detail': f'You are not allowed to run attribution model "{model_type}"'},
                status=status.HTTP_403_FORBIDDEN,
            )

        paths = ConversionPath.objects.prefetch_related('touchpoints').filter(converted=True)

        if model_type == 'custom_weight':
            weights = {
                'first_touch': serializer.validated_data.get('first_touch_weight'),
                'middle_touch': serializer.validated_data.get('middle_touch_weight'),
                'last_touch': serializer.validated_data.get('last_touch_weight'),
            }
            credits = MODELS[model_type](paths, weights=weights)
        else:
            credits = MODELS[model_type](paths)

        AttributionResult.objects.filter(model_type=model_type, created_by=request.user).delete()

        channel_ids = list(credits.keys())
        channel_map = {ch.pk: ch for ch in AdChannel.objects.filter(pk__in=channel_ids)}

        result_objs = [
            AttributionResult(
                model_type=model_type,
                channel=channel_map[channel_id],
                credit=credit,
                created_by=request.user,
            )
            for channel_id, credit in credits.items()
            if channel_id in channel_map
        ]
        AttributionResult.objects.bulk_create(result_objs)
        results = sorted(result_objs, key=lambda r: -r.credit)

        return Response(AttributionResultSerializer(results, many=True).data, status=status.HTTP_200_OK)


class AttributionResultViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AttributionResultSerializer

    def get_queryset(self):
        user = self.request.user
        role = get_user_role(user)
        qs = AttributionResult.objects.select_related('channel')

        if role == ROLE_ADMIN:
            pass
        elif role == ROLE_OPERATOR:
            allowed = get_allowed_models(user)
            if allowed is not None:
                qs = qs.filter(model_type__in=allowed)
        else:
            qs = qs.filter(created_by=user)

        model_type = self.request.query_params.get('model_type')
        if model_type:
            qs = qs.filter(model_type=model_type)
        return qs

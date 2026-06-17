from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.views import APIView

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
        paths = ConversionPath.objects.prefetch_related('touchpoints').filter(converted=True)
        credits = MODELS[model_type](paths)

        AttributionResult.objects.filter(model_type=model_type).delete()

        results = []
        for channel_id, credit in credits.items():
            channel = AdChannel.objects.get(pk=channel_id)
            result = AttributionResult.objects.create(
                model_type=model_type,
                channel=channel,
                credit=credit,
            )
            results.append(result)

        return Response(AttributionResultSerializer(results, many=True).data, status=status.HTTP_200_OK)


class AttributionResultViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AttributionResultSerializer

    def get_queryset(self):
        qs = AttributionResult.objects.select_related('channel').all()
        model_type = self.request.query_params.get('model_type')
        if model_type:
            qs = qs.filter(model_type=model_type)
        return qs

from django.db.models import Count
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.decorators import action

from apps.accounts.models import get_user_role, get_allowed_models, ROLE_ADMIN, ROLE_OPERATOR, ROLE_USER
from .models import AttributionResult, AttributionTask
from .serializers import (
    AttributionResultSerializer,
    RunAttributionSerializer,
    AttributionTaskSerializer,
)
from .tasks import acquire_or_get_existing_task, dispatch_attribution_task


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

        params = {}
        if model_type == 'custom_weight':
            for key in ('first_touch_weight', 'middle_touch_weight', 'last_touch_weight'):
                if key in serializer.validated_data:
                    params[key] = serializer.validated_data[key]

        task, is_new = acquire_or_get_existing_task(
            user_id=request.user.pk,
            model_type=model_type,
            params_dict=params,
        )

        if is_new and task.status == AttributionTask.STATUS_PENDING:
            dispatch_attribution_task(task.pk)

        return Response(
            {
                'task_id': task.pk,
                'status': task.status,
                'is_new': is_new,
            },
            status=status.HTTP_202_ACCEPTED,
        )


class AttributionTaskViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AttributionTaskSerializer

    def get_queryset(self):
        user = self.request.user
        role = get_user_role(user)
        qs = AttributionTask.objects.annotate(results_count=Count('results'))

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

        task_status = self.request.query_params.get('status')
        if task_status:
            qs = qs.filter(status=task_status)

        return qs

    @action(detail=True, methods=['get'], url_path='results')
    def results(self, request, pk=None):
        task = self.get_object()
        results = task.results.select_related('channel').all()
        serializer = AttributionResultSerializer(results, many=True)
        return Response(serializer.data)


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

        task_id = self.request.query_params.get('task_id')
        if task_id:
            qs = qs.filter(task_id=task_id)

        return qs

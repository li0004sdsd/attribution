from decimal import Decimal, InvalidOperation
from rest_framework import serializers
from .models import AttributionResult, AttributionTask
from apps.channels.serializers import AdChannelSerializer


class AttributionResultSerializer(serializers.ModelSerializer):
    channel_detail = AdChannelSerializer(source='channel', read_only=True)
    task_id = serializers.PrimaryKeyRelatedField(source='task', read_only=True)

    class Meta:
        model = AttributionResult
        fields = ('id', 'model_type', 'channel', 'channel_detail', 'credit', 'calculated_at',
                  'task_id', 'is_partial')
        read_only_fields = ('id', 'calculated_at', 'task_id', 'is_partial')


class RunAttributionSerializer(serializers.Serializer):
    model_type = serializers.ChoiceField(choices=['first_touch', 'last_touch', 'linear', 'custom_weight'])
    first_touch_weight = serializers.FloatField(required=False, min_value=0, max_value=1)
    middle_touch_weight = serializers.FloatField(required=False, min_value=0, max_value=1)
    last_touch_weight = serializers.FloatField(required=False, min_value=0, max_value=1)

    def validate(self, attrs):
        model_type = attrs.get('model_type')
        if model_type == 'custom_weight':
            w1 = attrs.get('first_touch_weight')
            w2 = attrs.get('middle_touch_weight')
            w3 = attrs.get('last_touch_weight')

            if w1 is not None and w2 is not None and w3 is not None:
                try:
                    total = Decimal(str(w1)) + Decimal(str(w2)) + Decimal(str(w3))
                except (InvalidOperation, TypeError, ValueError):
                    raise serializers.ValidationError('Invalid weight values')

                if abs(total - Decimal('1')) > Decimal('0.0001'):
                    raise serializers.ValidationError(
                        'Sum of first_touch_weight, middle_touch_weight, last_touch_weight must equal 1'
                    )
            elif not (w1 is None and w2 is None and w3 is None):
                raise serializers.ValidationError(
                    'Either all three weights must be provided, or none of them'
                )
        return attrs


class AttributionTaskSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    model_type_display = serializers.CharField(source='get_model_type_display', read_only=True)
    params = serializers.SerializerMethodField()
    results_count = serializers.IntegerField(read_only=True)
    created_by_id = serializers.PrimaryKeyRelatedField(source='created_by', read_only=True)

    class Meta:
        model = AttributionTask
        fields = (
            'id',
            'model_type',
            'model_type_display',
            'status',
            'status_display',
            'progress',
            'total_paths',
            'processed_paths',
            'error_message',
            'params',
            'created_by_id',
            'created_at',
            'started_at',
            'finished_at',
            'results_count',
        )
        read_only_fields = fields

    def get_params(self, obj):
        return obj.params


class TaskIdResponseSerializer(serializers.Serializer):
    task_id = serializers.IntegerField()
    status = serializers.CharField()
    is_new = serializers.BooleanField(
        help_text='True if a new task was created; False if an existing equivalent task was returned'
    )


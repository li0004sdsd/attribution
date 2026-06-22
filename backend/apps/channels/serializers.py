from rest_framework import serializers
from .models import AdChannel, DEFAULT_ATTRIBUTION_WINDOW_DAYS


class AdChannelSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdChannel
        fields = (
            'id',
            'name',
            'platform',
            'cost_per_click',
            'active',
            'attribution_window_days',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('id', 'created_at', 'updated_at')

    def validate_attribution_window_days(self, value):
        if value is None:
            return DEFAULT_ATTRIBUTION_WINDOW_DAYS
        if value < 1:
            raise serializers.ValidationError(
                'Attribution window must be at least 1 day'
            )
        if value > 3650:
            raise serializers.ValidationError(
                'Attribution window cannot exceed 3650 days (10 years)'
            )
        return value

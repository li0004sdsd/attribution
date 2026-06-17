from rest_framework import serializers
from .models import AttributionResult
from apps.channels.serializers import AdChannelSerializer


class AttributionResultSerializer(serializers.ModelSerializer):
    channel_detail = AdChannelSerializer(source='channel', read_only=True)

    class Meta:
        model = AttributionResult
        fields = ('id', 'model_type', 'channel', 'channel_detail', 'credit', 'calculated_at')
        read_only_fields = ('id', 'calculated_at')


class RunAttributionSerializer(serializers.Serializer):
    model_type = serializers.ChoiceField(choices=['first_touch', 'last_touch', 'linear'])

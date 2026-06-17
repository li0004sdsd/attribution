from rest_framework import serializers
from .models import AdChannel


class AdChannelSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdChannel
        fields = ('id', 'name', 'platform', 'cost_per_click', 'active', 'created_at', 'updated_at')
        read_only_fields = ('id', 'created_at', 'updated_at')

from rest_framework import serializers
from .models import ConversionPath, TouchPoint
from apps.channels.serializers import AdChannelSerializer


class TouchPointSerializer(serializers.ModelSerializer):
    channel_detail = AdChannelSerializer(source='channel', read_only=True)

    class Meta:
        model = TouchPoint
        fields = ('id', 'channel', 'channel_detail', 'timestamp', 'position')


class ConversionPathSerializer(serializers.ModelSerializer):
    touchpoints = TouchPointSerializer(many=True, read_only=True)

    class Meta:
        model = ConversionPath
        fields = ('id', 'user_id', 'converted', 'conversion_value', 'touchpoints', 'created_at')
        read_only_fields = ('id', 'created_at')


class BulkTouchPointSerializer(serializers.Serializer):
    channel = serializers.IntegerField()
    timestamp = serializers.DateTimeField()
    position = serializers.IntegerField()


class BulkImportSerializer(serializers.Serializer):
    user_id = serializers.CharField(max_length=200)
    converted = serializers.BooleanField(default=False)
    conversion_value = serializers.DecimalField(max_digits=12, decimal_places=2, default=0)
    touchpoints = BulkTouchPointSerializer(many=True)

    def create(self, validated_data):
        from apps.channels.models import AdChannel
        tps_data = validated_data.pop('touchpoints')

        existing = ConversionPath.objects.filter(user_id=validated_data['user_id']).first()
        if existing is not None:
            return existing, False

        path = ConversionPath.objects.create(**validated_data)
        for tp in tps_data:
            channel = AdChannel.objects.get(pk=tp['channel'])
            TouchPoint.objects.create(
                path=path,
                channel=channel,
                timestamp=tp['timestamp'],
                position=tp['position'],
            )
        return path, True

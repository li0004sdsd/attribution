from rest_framework import viewsets
from .models import AdChannel
from .serializers import AdChannelSerializer


class AdChannelViewSet(viewsets.ModelViewSet):
    queryset = AdChannel.objects.all()
    serializer_class = AdChannelSerializer

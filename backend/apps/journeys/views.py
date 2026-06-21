from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import ConversionPath, TouchPoint
from .serializers import ConversionPathSerializer, BulkImportSerializer


class ConversionPathViewSet(viewsets.ModelViewSet):
    queryset = ConversionPath.objects.prefetch_related('touchpoints__channel').all()
    serializer_class = ConversionPathSerializer


class BulkImportView(APIView):
    def post(self, request):
        serializer = BulkImportSerializer(data=request.data)
        if serializer.is_valid():
            path, created = serializer.save()
            data = ConversionPathSerializer(path).data
            data['skipped'] = not created
            if created:
                return Response(data, status=status.HTTP_201_CREATED)
            return Response(data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

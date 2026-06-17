from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ConversionPathViewSet, BulkImportView

router = DefaultRouter()
router.register(r'paths', ConversionPathViewSet, basename='path')

urlpatterns = [
    path('', include(router.urls)),
    path('bulk-import/', BulkImportView.as_view(), name='bulk_import'),
]

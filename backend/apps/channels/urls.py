from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AdChannelViewSet

router = DefaultRouter()
router.register(r'', AdChannelViewSet, basename='channel')

urlpatterns = [
    path('', include(router.urls)),
]

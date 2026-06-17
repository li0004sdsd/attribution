from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import RunAttributionView, AttributionResultViewSet

router = DefaultRouter()
router.register(r'results', AttributionResultViewSet, basename='result')

urlpatterns = [
    path('', include(router.urls)),
    path('run/', RunAttributionView.as_view(), name='run_attribution'),
]

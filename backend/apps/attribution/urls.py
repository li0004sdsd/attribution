from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import RunAttributionView, AttributionResultViewSet, AttributionTaskViewSet

router = DefaultRouter()
router.register(r'results', AttributionResultViewSet, basename='result')
router.register(r'tasks', AttributionTaskViewSet, basename='task')

urlpatterns = [
    path('', include(router.urls)),
    path('run/', RunAttributionView.as_view(), name='run_attribution'),
]

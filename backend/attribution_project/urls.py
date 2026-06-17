from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('apps.accounts.urls')),
    path('api/channels/', include('apps.channels.urls')),
    path('api/journeys/', include('apps.journeys.urls')),
    path('api/attribution/', include('apps.attribution.urls')),
]

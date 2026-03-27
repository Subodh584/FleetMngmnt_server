"""
URL configuration for Fleet Management API.
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

urlpatterns = [
    path('admin/', admin.site.urls),

    # API v1
    path('api/v1/', include('core.urls')),
    path('api/v1/fleet/', include('fleet.urls')),
    path('api/v1/trips/', include('trips.urls')),
    path('api/v1/maintenance/', include('maintenance.urls')),
    path('api/v1/comms/', include('comms.urls')),
    path('api/v1/ai/', include('ai_assistant.urls')),

    # OpenAPI schema & docs
    path('api/v1/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/v1/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/v1/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


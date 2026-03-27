from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

# ==========================================
# REST Framework Router Initialization
# ==========================================
router = DefaultRouter()

# Human interactions and passive tracking loops
router.register(r'messages', views.MessageViewSet, basename='message')
router.register(r'notifications', views.NotificationViewSet, basename='notification')

# Active Priority Alerts
router.register(r'sos-alerts', views.SOSAlertViewSet, basename='sos-alert')

urlpatterns = [
    # Router Inclusion
    path('', include(router.urls)),
]

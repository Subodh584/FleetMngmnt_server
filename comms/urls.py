from django.urls import include, path
from rest_framework.routers import DefaultRouter

from . import views

router = DefaultRouter()
router.register(r'messages', views.MessageViewSet, basename='message')
router.register(r'notifications', views.NotificationViewSet, basename='notification')
router.register(r'sos-alerts', views.SOSAlertViewSet, basename='sos-alert')

urlpatterns = [
    path('', include(router.urls)),
]

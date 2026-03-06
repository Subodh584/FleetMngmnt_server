"""
WebSocket URL routing for Django Channels.
"""

from django.urls import re_path

from comms.consumers import ChatConsumer, NotificationConsumer
from trips.consumers import GpsTrackingConsumer

websocket_urlpatterns = [
    re_path(r'ws/trips/(?P<trip_id>\d+)/gps/$', GpsTrackingConsumer.as_asgi()),
    re_path(r'ws/notifications/$', NotificationConsumer.as_asgi()),
    re_path(r'ws/chat/(?P<peer_id>\d+)/$', ChatConsumer.as_asgi()),
]

"""
ASGI config for Fleet Management project.

Supports both HTTP and WebSocket protocols via Django Channels.
"""

import os

from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app.settings')

# Initialize Django ASGI application early to populate AppRegistry
django_asgi_app = get_asgi_application()

# Import after Django setup
from core.middleware import JWTAuthMiddleware  # noqa: E402
from app.routing import websocket_urlpatterns  # noqa: E402

application = ProtocolTypeRouter(
    {
        'http': django_asgi_app,
        'websocket': JWTAuthMiddleware(
            URLRouter(websocket_urlpatterns)
        ),
    }
)

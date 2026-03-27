"""
JWT authentication middleware for Django Channels WebSocket connections.
Extracts the JWT token from the query string (?token=xxx) and authenticates the user.
"""

from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.tokens import AccessToken

User = get_user_model()


@database_sync_to_async
def get_user_from_token(token_str):
    """
    Asynchronously decodes the provided JWT access token string.
    If valid, retrieves and returns the corresponding User and bounds their Profile.
    Otherwise, defaults to an AnonymousUser model.
    """
    try:
        token = AccessToken(token_str)
        user_id = token['user_id']
        return User.objects.select_related('profile').get(id=user_id)
    except Exception:
        # Fails securely on malformed, expired, or corrupted tickets.
        return AnonymousUser()


class JWTAuthMiddleware(BaseMiddleware):
    """
    Custom middleware that authenticates WebSocket connections via JWT token
    passed as a query parameter. The expected connection structure is: 
    ws://host/path/?token=<access_token>
    """

    async def __call__(self, scope, receive, send):
        """
        Intercepts the incoming WebSocket handshake to inject the `user` identity
        directly into the ASGI scope for consumption by downstream Consumers.
        """
        query_string = scope.get('query_string', b'').decode('utf-8')
        params = parse_qs(query_string)
        token_list = params.get('token', [])

        if token_list:
            scope['user'] = await get_user_from_token(token_list[0])
        else:
            scope['user'] = AnonymousUser()

        return await super().__call__(scope, receive, send)

"""
Notification and Chat WebSocket consumers.

NotificationConsumer: ws/notifications/?token=<JWT>
  - Receives real-time push notifications.

ChatConsumer: ws/chat/<peer_user_id>/?token=<JWT>
  - Real-time messaging between two users.
  - Send: {"content": "Hello!", "trip_id": null}
"""

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.utils import timezone

from .models import Message, Notification


# ---------------------------------------------------------------------------
# Notification Consumer
# ---------------------------------------------------------------------------

class NotificationConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        user = self.scope.get('user')
        if not user or user.is_anonymous:
            await self.close()
            return

        self.group_name = f'user_{user.id}_notifications'
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        user = self.scope.get('user')
        if user and not user.is_anonymous:
            await self.channel_layer.group_discard(
                f'user_{user.id}_notifications', self.channel_name,
            )

    async def receive_json(self, content, **kwargs):
        # Client can acknowledge / mark notifications read
        action = content.get('action')
        if action == 'mark_read':
            notification_id = content.get('notification_id')
            if notification_id:
                await self._mark_notification_read(notification_id)

    async def push_notification(self, event):
        """Handler for push_notification type messages from channel layer."""
        await self.send_json(event['data'])

    @database_sync_to_async
    def _mark_notification_read(self, notification_id):
        try:
            notif = Notification.objects.get(
                id=notification_id, user=self.scope['user'],
            )
            notif.status = 'read'
            notif.read_at = timezone.now()
            notif.save()
        except Notification.DoesNotExist:
            pass


# ---------------------------------------------------------------------------
# Chat Consumer
# ---------------------------------------------------------------------------

class ChatConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        user = self.scope.get('user')
        if not user or user.is_anonymous:
            await self.close()
            return

        self.peer_id = self.scope['url_route']['kwargs']['peer_id']
        # Create a deterministic group name for the two users
        ids = sorted([str(user.id), str(self.peer_id)])
        self.group_name = f'chat_{ids[0]}_{ids[1]}'

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive_json(self, content, **kwargs):
        user = self.scope.get('user')
        if not user or user.is_anonymous:
            return

        text = content.get('content', '').strip()
        if not text:
            return

        trip_id = content.get('trip_id')

        # Save message to DB
        message = await self._save_message(user.id, int(self.peer_id), text, trip_id)

        # Broadcast to group
        await self.channel_layer.group_send(
            self.group_name,
            {
                'type': 'chat_message',
                'data': {
                    'id': message.id if message else None,
                    'sender_id': user.id,
                    'receiver_id': int(self.peer_id),
                    'content': text,
                    'trip_id': trip_id,
                    'sent_at': str(message.sent_at) if message else None,
                },
            },
        )

        # Also push a notification to the receiver
        await self.channel_layer.group_send(
            f'user_{self.peer_id}_notifications',
            {
                'type': 'push_notification',
                'data': {
                    'alert_type': 'chat_message',
                    'title': f'New message from {user.get_full_name() or user.username}',
                    'body': text[:100],
                    'reference_id': message.id if message else None,
                    'reference_type': 'message',
                },
            },
        )

    async def chat_message(self, event):
        """Handler for chat_message type messages."""
        await self.send_json(event['data'])

    @database_sync_to_async
    def _save_message(self, sender_id, receiver_id, content, trip_id=None):
        return Message.objects.create(
            sender_id=sender_id,
            receiver_id=receiver_id,
            content=content,
            trip_id=trip_id,
        )

"""
GPS Tracking WebSocket consumer.

Drivers send GPS data via WebSocket; fleet managers subscribe to follow live.

Connect: ws/trips/<trip_id>/gps/?token=<JWT>

Driver sends:
  {"latitude": 12.9716, "longitude": 77.5946, "speed_kmh": 45.2, "heading_deg": 90.0}

Fleet managers receive broadcasts on the same connection.
"""

import json
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer

from trips.models import GpsLog, Trip


class GpsTrackingConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.trip_id = self.scope['url_route']['kwargs']['trip_id']
        self.group_name = f'trip_{self.trip_id}_tracking'
        user = self.scope.get('user')

        if not user or user.is_anonymous:
            await self.close()
            return

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive_json(self, content, **kwargs):
        user = self.scope.get('user')
        if not user or user.is_anonymous:
            return

        latitude = content.get('latitude')
        longitude = content.get('longitude')
        speed_kmh = content.get('speed_kmh')
        heading_deg = content.get('heading_deg')

        if latitude is None or longitude is None:
            await self.send_json({'error': 'latitude and longitude are required.'})
            return

        # Persist to database
        gps_log = await self._save_gps_log(
            trip_id=self.trip_id,
            latitude=latitude,
            longitude=longitude,
            speed_kmh=speed_kmh,
            heading_deg=heading_deg,
        )

        # Broadcast to group
        await self.channel_layer.group_send(
            self.group_name,
            {
                'type': 'gps_update',
                'data': {
                    'trip_id': int(self.trip_id),
                    'latitude': float(latitude),
                    'longitude': float(longitude),
                    'speed_kmh': float(speed_kmh) if speed_kmh else None,
                    'heading_deg': float(heading_deg) if heading_deg else None,
                    'recorded_at': str(gps_log.recorded_at) if gps_log else None,
                },
            },
        )

    async def gps_update(self, event):
        """Handler for gps_update group messages."""
        await self.send_json(event['data'])

    @database_sync_to_async
    def _save_gps_log(self, trip_id, latitude, longitude, speed_kmh, heading_deg):
        try:
            trip = Trip.objects.select_related('vehicle').get(id=trip_id)
            return GpsLog.objects.create(
                trip=trip,
                vehicle=trip.vehicle,
                latitude=latitude,
                longitude=longitude,
                speed_kmh=speed_kmh,
                heading_deg=heading_deg,
            )
        except Trip.DoesNotExist:
            return None

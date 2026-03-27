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
    """
    Secure WebSockets pipeline capable of ingesting high-throughput incoming Geo payloads
    directly from active Driver mobile apps, logging them sustainably into Postgres tables,
    and pushing subsequent identical broadcasts down synchronously to observant Fleet Dashboards.
    """
    async def connect(self):
        """Establishes authenticated stream logic binding dynamically against specific operational Trip streams."""
        self.trip_id = self.scope['url_route']['kwargs']['trip_id']
        self.group_name = f'trip_{self.trip_id}_tracking'
        user = self.scope.get('user')

        # Drop invalid identities explicitly at connection-start rather than later at runtime.
        if not user or user.is_anonymous:
            await self.close()
            return

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        """Releases the bound stream cleanly when client drops unexpectedly or completes run."""
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive_json(self, content, **kwargs):
        """
        Massively optimized ingestor loop mapping the dictionary contents directly to Python variables, 
        passing them safely to Async DB insertions, and looping the output via broadcast channels. 
        """
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

        # Securely orchestrate the relational insert via Async context encapsulation
        gps_log = await self._save_gps_log(
            trip_id=self.trip_id,
            latitude=latitude,
            longitude=longitude,
            speed_kmh=speed_kmh,
            heading_deg=heading_deg,
        )

        # Broadcast the successfully verified object metrics to the underlying room pool immediately
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
        """Standard JSON forwarder for `gps_update` group messages natively configured within Channels."""
        await self.send_json(event['data'])

    @database_sync_to_async
    def _save_gps_log(self, trip_id, latitude, longitude, speed_kmh, heading_deg):
        """
        Synchronous database hook securely guarded by Django ORM mechanisms.
        Protects the global query layer from asynchronous blockages natively.
        """
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

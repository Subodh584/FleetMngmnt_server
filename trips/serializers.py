from rest_framework import serializers

from core.models import Location
from core.serializers import UserSerializer
from fleet.serializers import VehicleSerializer
from .models import (
    Order, OrderDropPoint, Trip, Route, RouteDeviation,
    GpsLog, GeofenceEvent, TripExpense, FuelLog, DeliveryProof,
    DriverLocation, OdometerImage,
)


# ---------------------------------------------------------------------------
# Inline Location (Used strictly inside deep trip briefing maps)
# ---------------------------------------------------------------------------

class InlineLocationSerializer(serializers.ModelSerializer):
    """Read-only breakdown of a physical location context."""
    class Meta:
        model = Location
        fields = ['id', 'name', 'address', 'latitude', 'longitude', 'is_warehouse']


# ---------------------------------------------------------------------------
# Inline Drop Point (Used inside trip briefing destinations)
# ---------------------------------------------------------------------------

class InlineDropPointSerializer(serializers.ModelSerializer):
    """Extends individual destinations to contain actual coordinate geography under `location`."""
    location = InlineLocationSerializer(read_only=True)

    class Meta:
        model = OrderDropPoint
        fields = [
            'id', 'sequence_no', 'location',
            'contact_name', 'contact_phone', 'notes',
            'status', 'eta', 'arrived_at', 'delivered_at',
        ]


# ---------------------------------------------------------------------------
# Orders
# ---------------------------------------------------------------------------

class OrderDropPointSerializer(serializers.ModelSerializer):
    """Standard deserialization matching an active Order Drop Point node."""
    class Meta:
        model = OrderDropPoint
        fields = '__all__'
        read_only_fields = ['order', 'created_at']
        # arrived_at / delivered_at are auto-set by the viewset's perform_update
        # but kept writable at the serializer level so save(**extra) can securely attach them internally


class OrderDropPointWriteSerializer(serializers.Serializer):
    """Unbound ingestion shell for staging bulk insertions of new route destinations."""
    location_id = serializers.IntegerField()
    sequence_no = serializers.IntegerField()
    contact_name = serializers.CharField(max_length=150, required=False, default='')
    contact_phone = serializers.CharField(max_length=20, required=False, default='')
    notes = serializers.CharField(required=False, default='')


class BulkDropPointSerializer(serializers.Serializer):
    """Used specifically for mapping PATCH /orders/{id}/drop_points/ where it replaces all drop points."""
    drop_points = OrderDropPointWriteSerializer(many=True)

    def validate_drop_points(self, value):
        if not value:
            raise serializers.ValidationError('drop_points must contain at least one entry.')
        seq_nums = [item['sequence_no'] for item in value]
        if len(seq_nums) != len(set(seq_nums)):
            raise serializers.ValidationError('sequence_no values must be strictly unique within the list.')
        return value


class OrderSerializer(serializers.ModelSerializer):
    """Core translation of the Order entity, packaging the nested list of its route points natively."""
    drop_points = OrderDropPointSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = '__all__'
        read_only_fields = ['created_by', 'created_at', 'updated_at']


class OrderCreateSerializer(serializers.ModelSerializer):
    """Asynchronous payload resolver that creates an Order while generating its DropPoints efficiently."""
    drop_points = OrderDropPointWriteSerializer(many=True, write_only=True)

    class Meta:
        model = Order
        fields = ['order_ref', 'warehouse', 'notes', 'capacity_litre', 'capacity_kg', 'drop_points']

    def create(self, validated_data):
        drop_points_data = validated_data.pop('drop_points')
        user = self.context['request'].user
        
        order = Order.objects.create(created_by=user, **validated_data)
        
        # Hydrate all destination drops via bulk memory mapping to reduce I/O overhead
        drop_objs = [
            OrderDropPoint(
                order=order,
                location_id=dp['location_id'],
                sequence_no=dp['sequence_no'],
                contact_name=dp.get('contact_name', ''),
                contact_phone=dp.get('contact_phone', ''),
                notes=dp.get('notes', ''),
            )
            for dp in drop_points_data
        ]
        OrderDropPoint.objects.bulk_create(drop_objs)
        return order

    def to_representation(self, instance):
        # Reparse through the standard readable map instead of retaining raw write forms
        return OrderSerializer(instance).data


# ---------------------------------------------------------------------------
# Trips
# ---------------------------------------------------------------------------

class RouteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Route
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']


class TripSerializer(serializers.ModelSerializer):
    """
    Comprehensive mapping payload summarizing all driver constraints, contexts,
    and routing geometries into one massive unified state tree.
    """
    route_detail = RouteSerializer(read_only=True)
    vehicle_detail = VehicleSerializer(source='vehicle', read_only=True)
    driver_detail = UserSerializer(source='driver', read_only=True)
    
    # Method-injected dynamic mappings referencing nested relational data safely
    source = serializers.SerializerMethodField()
    destinations = serializers.SerializerMethodField()

    class Meta:
        model = Trip
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']

    def get_source(self, obj):
        """Resolves the physical Warehouse geography dynamically where the trip commences."""
        try:
            warehouse = obj.order.warehouse
            return InlineLocationSerializer(warehouse).data
        except Exception:
            return None

    def get_destinations(self, obj):
        """Retrieves and sequentially arranges all drop requirements tied underneath the bound Order."""
        try:
            drop_points = obj.order.drop_points.select_related('location').order_by('sequence_no')
            return InlineDropPointSerializer(drop_points, many=True).data
        except Exception:
            return []


class TripCreateSerializer(serializers.ModelSerializer):
    """Strict instantiation wrapper tying drivers and assets to their dispatch tasks."""
    class Meta:
        model = Trip
        fields = [
            'order', 'vehicle', 'driver', 'scheduled_start',
            'start_mileage_km',
        ]

    def create(self, validated_data):
        user = self.context['request'].user
        trip = Trip.objects.create(assigned_by=user, **validated_data)
        return trip

    def to_representation(self, instance):
        return TripSerializer(instance).data


# ---------------------------------------------------------------------------
# Route Deviations
# ---------------------------------------------------------------------------

class RouteDeviationSerializer(serializers.ModelSerializer):
    class Meta:
        model = RouteDeviation
        fields = '__all__'
        read_only_fields = ['detected_at']


# ---------------------------------------------------------------------------
# GPS
# ---------------------------------------------------------------------------

class GpsLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = GpsLog
        fields = '__all__'
        read_only_fields = ['recorded_at']


# ---------------------------------------------------------------------------
# Geofence Events
# ---------------------------------------------------------------------------

class GeofenceEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = GeofenceEvent
        fields = '__all__'
        read_only_fields = ['occurred_at']


# ---------------------------------------------------------------------------
# Expenses & Fuel
# ---------------------------------------------------------------------------

class TripExpenseSerializer(serializers.ModelSerializer):
    class Meta:
        model = TripExpense
        fields = '__all__'
        read_only_fields = ['driver', 'recorded_at', 'created_at']


class FuelLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = FuelLog
        fields = '__all__'
        read_only_fields = ['driver', 'vehicle', 'logged_at']


# ---------------------------------------------------------------------------
# Driver Location Stream
# ---------------------------------------------------------------------------

class DriverLocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = DriverLocation
        fields = '__all__'
        read_only_fields = ['updated_at']


class DriverLocationUpdateSerializer(serializers.Serializer):
    """High-throughput lightweight struct for ingesting repeated WebSocket/REST pings."""
    trip_id = serializers.IntegerField()
    latitude = serializers.DecimalField(max_digits=10, decimal_places=7)
    longitude = serializers.DecimalField(max_digits=10, decimal_places=7)
    speed_kmh = serializers.DecimalField(max_digits=6, decimal_places=2, required=False, allow_null=True)
    heading_deg = serializers.DecimalField(max_digits=5, decimal_places=2, required=False, allow_null=True)


# ---------------------------------------------------------------------------
# Delivery Proof
# ---------------------------------------------------------------------------

class DeliveryProofSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliveryProof
        fields = '__all__'
        read_only_fields = ['driver', 'submitted_at', 'verified_by', 'verified_at']


# ---------------------------------------------------------------------------
# Odometer Images
# ---------------------------------------------------------------------------

class OdometerImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = OdometerImage
        fields = '__all__'
        read_only_fields = ['driver', 'vehicle', 'recorded_at']

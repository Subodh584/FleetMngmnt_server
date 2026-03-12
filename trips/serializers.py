from rest_framework import serializers

from core.models import Location
from .models import (
    Order, OrderDropPoint, Trip, Route, RouteDeviation,
    GpsLog, GeofenceEvent, TripExpense, FuelLog, DeliveryProof,
)


# ---------------------------------------------------------------------------
# Inline location (used inside trip briefing)
# ---------------------------------------------------------------------------

class InlineLocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Location
        fields = ['id', 'name', 'address', 'latitude', 'longitude', 'is_warehouse']


# ---------------------------------------------------------------------------
# Inline drop point (used inside trip briefing destinations)
# ---------------------------------------------------------------------------

class InlineDropPointSerializer(serializers.ModelSerializer):
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
    class Meta:
        model = OrderDropPoint
        fields = '__all__'
        read_only_fields = ['order', 'arrived_at', 'delivered_at', 'created_at']


class OrderDropPointWriteSerializer(serializers.Serializer):
    location_id = serializers.IntegerField()
    sequence_no = serializers.IntegerField()
    contact_name = serializers.CharField(max_length=150, required=False, default='')
    contact_phone = serializers.CharField(max_length=20, required=False, default='')
    notes = serializers.CharField(required=False, default='')


class BulkDropPointSerializer(serializers.Serializer):
    """Used for PATCH /orders/{id}/drop_points/ — replaces all drop points."""
    drop_points = OrderDropPointWriteSerializer(many=True)

    def validate_drop_points(self, value):
        if not value:
            raise serializers.ValidationError('drop_points must contain at least one entry.')
        seq_nums = [item['sequence_no'] for item in value]
        if len(seq_nums) != len(set(seq_nums)):
            raise serializers.ValidationError('sequence_no values must be unique within the list.')
        return value


class OrderSerializer(serializers.ModelSerializer):
    drop_points = OrderDropPointSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = '__all__'
        read_only_fields = ['created_by', 'created_at', 'updated_at']


class OrderCreateSerializer(serializers.ModelSerializer):
    drop_points = OrderDropPointWriteSerializer(many=True, write_only=True)

    class Meta:
        model = Order
        fields = ['order_ref', 'warehouse', 'notes', 'drop_points']

    def create(self, validated_data):
        drop_points_data = validated_data.pop('drop_points')
        user = self.context['request'].user
        order = Order.objects.create(created_by=user, **validated_data)
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
    route_detail = RouteSerializer(read_only=True)
    source = serializers.SerializerMethodField()
    destinations = serializers.SerializerMethodField()

    class Meta:
        model = Trip
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']

    def get_source(self, obj):
        """Warehouse the trip departs from."""
        try:
            warehouse = obj.order.warehouse
            return InlineLocationSerializer(warehouse).data
        except Exception:
            return None

    def get_destinations(self, obj):
        """All ordered drop points for the trip's order."""
        try:
            drop_points = obj.order.drop_points.select_related('location').order_by('sequence_no')
            return InlineDropPointSerializer(drop_points, many=True).data
        except Exception:
            return []


class TripCreateSerializer(serializers.ModelSerializer):
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
# Route deviations
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
# Geofence events
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
        read_only_fields = ['logged_at']


# ---------------------------------------------------------------------------
# Delivery proof
# ---------------------------------------------------------------------------

class DeliveryProofSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliveryProof
        fields = '__all__'
        read_only_fields = ['driver', 'submitted_at', 'verified_by', 'verified_at']

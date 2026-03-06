from rest_framework import serializers

from .models import (
    Order, OrderDropPoint, Trip, Route, RouteDeviation,
    GpsLog, GeofenceEvent, TripExpense, FuelLog, DeliveryProof,
)


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

    class Meta:
        model = Trip
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']


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

from django.conf import settings
from django.db import models


class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('assigned', 'Assigned'),
        ('in_transit', 'In Transit'),
        ('delivered', 'Delivered'),
        ('failed', 'Failed'),
    ]

    order_ref = models.CharField(max_length=50, unique=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='created_orders',
    )
    warehouse = models.ForeignKey(
        'core.Location', on_delete=models.CASCADE, related_name='orders',
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    notes = models.TextField(blank=True, default='')
    capacity_litre = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    capacity_kg = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'orders'

    def __str__(self):
        return self.order_ref


class OrderDropPoint(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_transit', 'In Transit'),
        ('arrived', 'Arrived'),
        ('delivered', 'Delivered'),
        ('failed', 'Failed'),
    ]

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='drop_points')
    location = models.ForeignKey(
        'core.Location', on_delete=models.CASCADE, related_name='drop_points',
    )
    sequence_no = models.IntegerField()
    contact_name = models.CharField(max_length=150, blank=True, default='')
    contact_phone = models.CharField(max_length=20, blank=True, default='')
    notes = models.TextField(blank=True, default='')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    eta = models.DateTimeField(null=True, blank=True)
    arrived_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'order_drop_points'
        unique_together = [('order', 'sequence_no')]
        ordering = ['sequence_no']

    def __str__(self):
        return f'Order {self.order.order_ref} – Drop #{self.sequence_no}'


class Trip(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('assigned', 'Assigned'),
        ('accepted', 'Accepted'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('rejected', 'Rejected'),
        ('delayed', 'Delayed'),
    ]

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='trips')
    vehicle = models.ForeignKey(
        'fleet.Vehicle', on_delete=models.CASCADE, related_name='trips',
    )
    driver = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='trips',
    )
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='assigned_trips',
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='assigned')
    route = models.OneToOneField(
        'Route', on_delete=models.SET_NULL, null=True, blank=True, related_name='trip_ref',
    )
    start_mileage_km = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    end_mileage_km = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    start_location_lat = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    start_location_lng = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    end_location_lat = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    end_location_lng = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    rejection_reason = models.TextField(blank=True, default='')
    started_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    scheduled_start = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'trips'

    def __str__(self):
        return f'Trip #{self.pk} – {self.order.order_ref}'


class Route(models.Model):
    trip = models.OneToOneField(Trip, on_delete=models.CASCADE, related_name='route_detail')
    origin_lat = models.DecimalField(max_digits=10, decimal_places=7)
    origin_lng = models.DecimalField(max_digits=10, decimal_places=7)
    destination_lat = models.DecimalField(max_digits=10, decimal_places=7)
    destination_lng = models.DecimalField(max_digits=10, decimal_places=7)
    optimized_path = models.JSONField(null=True, blank=True)
    total_distance_km = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    estimated_duration_min = models.IntegerField(null=True, blank=True)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='approved_routes',
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'routes'

    def __str__(self):
        return f'Route for Trip #{self.trip_id}'


class RouteDeviation(models.Model):
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name='route_deviations')
    latitude = models.DecimalField(max_digits=10, decimal_places=7)
    longitude = models.DecimalField(max_digits=10, decimal_places=7)
    deviation_meters = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    detected_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'route_deviations'

    def __str__(self):
        return f'Deviation on Trip #{self.trip_id}'


class GpsLog(models.Model):
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name='gps_logs')
    vehicle = models.ForeignKey(
        'fleet.Vehicle', on_delete=models.CASCADE, related_name='gps_logs',
    )
    latitude = models.DecimalField(max_digits=10, decimal_places=7)
    longitude = models.DecimalField(max_digits=10, decimal_places=7)
    speed_kmh = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    heading_deg = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    recorded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'gps_logs'
        indexes = [
            models.Index(fields=['trip'], name='idx_gps_logs_trip'),
            models.Index(fields=['-recorded_at'], name='idx_gps_logs_recorded'),
        ]

    def __str__(self):
        return f'GPS #{self.pk} – Trip #{self.trip_id}'


class GeofenceEvent(models.Model):
    EVENT_TYPE_CHOICES = [
        ('entry', 'Entry'),
        ('exit', 'Exit'),
    ]

    trip = models.ForeignKey(
        Trip, on_delete=models.CASCADE, null=True, blank=True, related_name='geofence_events',
    )
    vehicle = models.ForeignKey(
        'fleet.Vehicle', on_delete=models.CASCADE, related_name='geofence_events',
    )
    geofence = models.ForeignKey(
        'core.Geofence', on_delete=models.CASCADE, related_name='events',
    )
    drop_point = models.ForeignKey(
        OrderDropPoint, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='geofence_events',
    )
    event_type = models.CharField(max_length=10, choices=EVENT_TYPE_CHOICES)
    latitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    longitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    occurred_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'geofence_events'

    def __str__(self):
        return f'{self.event_type} – Geofence {self.geofence_id}'


class TripExpense(models.Model):
    EXPENSE_TYPE_CHOICES = [
        ('fuel', 'Fuel'),
        ('toll', 'Toll'),
        ('parking', 'Parking'),
        ('other', 'Other'),
    ]

    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name='expenses')
    driver = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='trip_expenses',
    )
    expense_type = models.CharField(max_length=20, choices=EXPENSE_TYPE_CHOICES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='INR')
    description = models.TextField(blank=True, default='')
    receipt_url = models.URLField(blank=True, default='')
    receipt_image = models.ImageField(upload_to='expense_receipts/', blank=True, null=True)
    recorded_at = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'trip_expenses'

    def __str__(self):
        return f'{self.expense_type} – ₹{self.amount}'


class FuelLog(models.Model):
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name='fuel_logs')
    vehicle = models.ForeignKey(
        'fleet.Vehicle', on_delete=models.CASCADE, related_name='fuel_logs',
    )
    driver = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='fuel_logs',
    )
    fuel_amount_liters = models.DecimalField(max_digits=8, decimal_places=2)
    cost_per_liter = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    total_cost = models.DecimalField(max_digits=10, decimal_places=2)
    odometer_km = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    fuel_station = models.CharField(max_length=200, blank=True, default='')
    receipt_url = models.URLField(blank=True, default='')
    receipt_image = models.ImageField(upload_to='fuel_receipts/', blank=True, null=True)
    logged_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'fuel_logs'

    def __str__(self):
        return f'Fuel: {self.fuel_amount_liters}L – Trip #{self.trip_id}'


class DriverLocation(models.Model):
    """Current location of a driver on a trip. One row per trip+driver, upserted on each update."""
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name='driver_locations')
    driver = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='driver_locations',
    )
    vehicle = models.ForeignKey(
        'fleet.Vehicle', on_delete=models.CASCADE, related_name='driver_locations',
    )
    latitude = models.DecimalField(max_digits=10, decimal_places=7)
    longitude = models.DecimalField(max_digits=10, decimal_places=7)
    speed_kmh = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    heading_deg = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'driver_locations'
        unique_together = [('trip', 'driver')]

    def __str__(self):
        return f'Location – Driver {self.driver_id} on Trip #{self.trip_id}'


class DeliveryProof(models.Model):
    PROOF_TYPE_CHOICES = [
        ('photo', 'Photo'),
        ('signature', 'Signature'),
        ('digital_confirmation', 'Digital Confirmation'),
    ]

    drop_point = models.ForeignKey(
        OrderDropPoint, on_delete=models.CASCADE, related_name='delivery_proofs',
    )
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name='delivery_proofs')
    driver = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='delivery_proofs',
    )
    proof_type = models.CharField(max_length=25, choices=PROOF_TYPE_CHOICES)
    file_url = models.FileField(upload_to='delivery_proofs/', blank=True, null=True)
    digital_confirmation_code = models.CharField(max_length=100, blank=True, default='')
    latitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    longitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='verified_proofs',
    )
    verified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'delivery_proofs'

    def __str__(self):
        return f'Proof ({self.proof_type}) – Drop #{self.drop_point_id}'


class OdometerImage(models.Model):
    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name='odometer_images')
    vehicle = models.ForeignKey(
        'fleet.Vehicle', on_delete=models.CASCADE, related_name='odometer_images',
    )
    driver = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='odometer_images',
    )
    image = models.ImageField(upload_to='odometer_images/')
    odometer_reading_km = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    recorded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'odometer_images'

    def __str__(self):
        return f'Odometer – Trip #{self.trip_id} – {self.recorded_at}'

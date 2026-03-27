from django.conf import settings
from django.db import models


class Vehicle(models.Model):
    """
    Represents an operational vehicle within the fleet.
    Tracks essential metadata, running metrics (like mileage), and current status
    to evaluate availability for Dispatch.
    """
    STATUS_CHOICES = [
        ('available', 'Available'),
        ('in_trip', 'In Trip'),
        ('idle', 'Idle'),
        ('under_maintenance', 'Under Maintenance'),
    ]

    # Core Identifiers
    registration_no = models.CharField(max_length=50, unique=True)
    make = models.CharField(max_length=100)
    model = models.CharField(max_length=100)
    year = models.IntegerField(null=True, blank=True)
    vin = models.CharField(max_length=100, unique=True, null=True, blank=True)
    
    # Specs
    fuel_type = models.CharField(max_length=30, blank=True, default='')
    capacity_kg = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    capacity_litre = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Operational Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='available')
    current_mileage_km = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Maintenance tracking points
    last_service_date = models.DateField(null=True, blank=True)
    next_service_due_km = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    next_service_due_date = models.DateField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'vehicles'

    def __str__(self):
        return f'{self.registration_no} – {self.make} {self.model}'


class InspectionChecklist(models.Model):
    """
    A template containing a preset collection of Checklist Items.
    For instance: 'Pre-Trip Checklist' or 'Post-Trip Checklist'.
    """
    name = models.CharField(max_length=150)
    
    # Permits soft-archiving outdated checklists without destroying history
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'inspection_checklists'

    def __str__(self):
        return self.name


class InspectionChecklistItem(models.Model):
    """
    A specific question or visual check required on a given InspectionChecklist.
    Example: 'Check tire pressure' or 'Verify brake fluid'.
    """
    checklist = models.ForeignKey(
        InspectionChecklist, on_delete=models.CASCADE, related_name='items',
    )
    item_name = models.CharField(max_length=200)
    
    # Enforces the rendering order on the client app GUI
    sequence_no = models.IntegerField()
    is_required = models.BooleanField(default=True)

    class Meta:
        db_table = 'inspection_checklist_items'
        ordering = ['sequence_no']

    def __str__(self):
        return self.item_name


class Inspection(models.Model):
    """
    A master record generated anytime a driver evaluates a vehicle against a checklist.
    Can be tied to a standard Trip or submitted Ad-Hoc.
    """
    INSPECTION_TYPE_CHOICES = [
        ('pre_trip', 'Pre-Trip'),
        ('post_trip', 'Post-Trip'),
        ('ad_hoc', 'Ad-Hoc'),
    ]
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('flagged', 'Flagged'),
        ('maintenance_scheduled', 'Maintenance Scheduled'),
    ]

    # Context Pointers
    trip = models.ForeignKey(
        'trips.Trip', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='inspections',
    )
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='inspections')
    driver = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='inspections',
    )
    checklist = models.ForeignKey(
        InspectionChecklist, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='inspections',
    )
    
    # Categorization and Triage logic
    inspection_type = models.CharField(
        max_length=20, choices=INSPECTION_TYPE_CHOICES, default='pre_trip',
    )
    overall_status = models.CharField(
        max_length=30, choices=STATUS_CHOICES, default='pending',
    )
    notes = models.TextField(blank=True, default='')
    
    # Authorization checks
    approved = models.BooleanField(default=False)
    assigned_to_manager = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='assigned_inspections',
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='reviewed_inspections',
    )
    
    # Timestamps
    reviewed_at = models.DateTimeField(null=True, blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'inspections'

    def __str__(self):
        return f'Inspection #{self.pk} – {self.vehicle}'


class InspectionResult(models.Model):
    """
    A single evaluation corresponding to one item inside a driver's submitted Inspection.
    Stores PASS/FAIL outcomes along with specific attached evidence (notes, photos).
    """
    RESULT_CHOICES = [
        ('pass', 'Pass'),
        ('fail', 'Fail'),
        ('na', 'N/A'),
    ]

    inspection = models.ForeignKey(
        Inspection, on_delete=models.CASCADE, related_name='results',
    )
    checklist_item = models.ForeignKey(
        InspectionChecklistItem, on_delete=models.CASCADE, related_name='results',
    )
    result = models.CharField(max_length=10, choices=RESULT_CHOICES)
    
    # Additional Context
    notes = models.TextField(blank=True, default='')
    photo_url = models.URLField(blank=True, default='')

    class Meta:
        db_table = 'inspection_results'

    def __str__(self):
        return f'{self.checklist_item.item_name}: {self.result}'


class VehicleIssue(models.Model):
    """
    A persistent problem tracked against a specific vehicle.
    Often triggered by a "fail" condition within an InspectionResult, 
    but can also be arbitrarily lodged by a driver mapping mid-trip hazards.
    """
    SEVERITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]
    STATUS_CHOICES = [
        ('reported', 'Reported'),
        ('acknowledged', 'Acknowledged'),
        ('in_repair', 'In Repair'),
        ('resolved', 'Resolved'),
    ]

    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name='issues')
    reported_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reported_issues',
    )
    
    # The source Inspection where this flaw was flagged, if applicable
    inspection = models.ForeignKey(
        Inspection, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='issues',
    )
    
    # Fleet manager who has taken ownership of this issue.
    # Null = unacknowledged, visible to all managers.
    # Auto-set when a manager acknowledges (status → acknowledged).
    assigned_to_manager = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='managed_issues',
    )
    
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default='')
    severity = models.CharField(max_length=10, choices=SEVERITY_CHOICES, default='medium')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='reported')
    photo_url = models.URLField(blank=True, default='')
    
    # Lifecycle
    approved = models.BooleanField(default=False)
    reported_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'vehicle_issues'

    def __str__(self):
        return f'{self.title} – {self.vehicle}'

from django.conf import settings
from django.db import models


class MaintenanceSchedule(models.Model):
    """
    Tracks planned upcoming service routines. Allows Fleet Managers to project
    vehicle downtime before physical dispatch blocking occurs.
    """
    MAINTENANCE_TYPE_CHOICES = [
        ('preventive', 'Preventive'),
        ('corrective', 'Corrective'),
        ('emergency', 'Emergency'),
    ]
    STATUS_CHOICES = [
        ('scheduled', 'Scheduled'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    vehicle = models.ForeignKey(
        'fleet.Vehicle', on_delete=models.CASCADE, related_name='maintenance_schedules',
    )
    scheduled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='scheduled_maintenances',
    )
    maintenance_type = models.CharField(max_length=20, choices=MAINTENANCE_TYPE_CHOICES)
    description = models.TextField()
    scheduled_date = models.DateField()
    estimated_duration_hours = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')
    notes = models.TextField(blank=True, default='')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'maintenance_schedules'

    def __str__(self):
        return f'Schedule #{self.pk} – {self.vehicle}'


class MaintenanceRecord(models.Model):
    """
    Represents an active or historically completed physical repair session in the garage.
    Links back to scheduled routines or spontaneously reported Fleet Issues natively.
    """
    MAINTENANCE_TYPE_CHOICES = MaintenanceSchedule.MAINTENANCE_TYPE_CHOICES
    REPAIR_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]

    vehicle = models.ForeignKey(
        'fleet.Vehicle', on_delete=models.CASCADE, related_name='maintenance_records',
    )
    schedule = models.ForeignKey(
        MaintenanceSchedule, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='records',
    )
    issue = models.ForeignKey(
        'fleet.VehicleIssue', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='maintenance_records',
    )
    maintenance_type = models.CharField(max_length=20, choices=MAINTENANCE_TYPE_CHOICES)
    description = models.TextField()
    repair_status = models.CharField(max_length=20, choices=REPAIR_STATUS_CHOICES, default='pending')
    
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='assigned_maintenance_records',
    )
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='delegated_maintenance_records',
    )
    
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    total_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    mileage_at_service = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    technician_notes = models.TextField(blank=True, default='')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'maintenance_records'

    def __str__(self):
        return f'Record #{self.pk} – {self.vehicle}'


class SparePart(models.Model):
    """
    Represents a decoupled internal physical part. Typically links dynamically 
    when an operation needs explicit stock consumption tracking beyond generalized accounting. 
    """
    maintenance = models.ForeignKey(
        MaintenanceRecord, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='parts',
    )
    part_name = models.TextField()
    part_number = models.TextField(blank=True, null=True)
    quantity = models.TextField(blank=True, null=True)
    unit_cost = models.TextField(blank=True, null=True)
    total_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'spare_parts'
        verbose_name = 'Spare Part'

    def save(self, *args, **kwargs):
        """Calculates derived absolute costs transparently."""
        try:
            if self.quantity and self.unit_cost:
                self.total_cost = float(self.quantity) * float(self.unit_cost)
        except (ValueError, TypeError):
            pass
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.part_name} x{self.quantity}'


class SparePartUsed(models.Model):
    """
    Acts as a definitive ledger entry specifying exact parts consumed during a MaintenanceRecord.
    Strictly calculates ledger expenditure implicitly on SQL insert.
    """
    maintenance = models.ForeignKey(
        MaintenanceRecord, on_delete=models.CASCADE, related_name='spare_parts',
    )
    part_name = models.CharField(max_length=200)
    part_number = models.CharField(max_length=100, blank=True, default='')
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    total_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'spare_parts_used'

    def save(self, *args, **kwargs):
        """Auto-calculate total to prevent API mathematical inconsistencies or malicious manual overrides."""
        if self.quantity and self.unit_cost:
            self.total_cost = self.quantity * self.unit_cost
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.part_name} x{self.quantity}'

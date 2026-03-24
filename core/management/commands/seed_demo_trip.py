"""
Management command to seed ONE complete demo trip with a live driver location.

Creates:
  1. Source warehouse Location  (Hyderabad depot)
  2. Two drop-point Locations   (Bangalore, Chennai)
  3. An Order linking warehouse → drop points
  4. A Trip assigned to an existing driver + vehicle
  5. A Route with waypoints
  6. A DriverLocation entry (driver sitting at the warehouse, ready to depart)

Usage:
    python manage.py seed_demo_trip
    python manage.py seed_demo_trip --flush   # deletes this demo trip first, then re-creates
"""

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from core.models import Location
from fleet.models import Vehicle
from trips.models import (
    DriverLocation,
    Order,
    OrderDropPoint,
    Route,
    Trip,
)

User = get_user_model()

# ---------------------------------------------------------------------------
# Hardcoded demo coordinates (realistic Indian cities)
# ---------------------------------------------------------------------------

# Source: Hyderabad (TSRTC depot area – driver starting point)
SOURCE_LAT  = Decimal("17.4435000")
SOURCE_LNG  = Decimal("78.3772000")

# Drop point 1: Bangalore city centre
DROP1_LAT   = Decimal("12.9716000")
DROP1_LNG   = Decimal("77.5946000")

# Drop point 2: Chennai central
DROP2_LAT   = Decimal("13.0827000")
DROP2_LNG   = Decimal("80.2707000")

# Driver's current position (parked at the Hyderabad warehouse)
DRIVER_LAT  = Decimal("17.4435100")
DRIVER_LNG  = Decimal("78.3772200")

ORDER_REF   = "ORD-DEMO-9999"


class Command(BaseCommand):
    help = "Seed one demo trip with driver location for UI testing."

    def add_arguments(self, parser):
        parser.add_argument(
            "--flush",
            action="store_true",
            help="Delete the demo trip (ORDER_REF=ORD-DEMO-9999) before re-creating.",
        )

    def handle(self, *args, **options):
        if options["flush"]:
            self._flush()

        self._seed()

    # ------------------------------------------------------------------
    def _flush(self):
        self.stdout.write("Flushing previous demo trip …")
        Order.objects.filter(order_ref=ORDER_REF).delete()
        Location.objects.filter(name__startswith="[DEMO]").delete()
        self.stdout.write(self.style.SUCCESS("  ✓ Flushed"))

    # ------------------------------------------------------------------
    def _seed(self):
        # ── 1. Find an existing driver ─────────────────────────────────
        driver = (
            User.objects.filter(profile__role="driver", is_active=True)
            .order_by("id")
            .first()
        )
        if not driver:
            self.stdout.write(self.style.ERROR(
                "No driver user found. Run `seed_data` first."
            ))
            return
        self.stdout.write(f"  Driver  : {driver.username} (id={driver.id})")

        # ── 2. Find a fleet manager (for assigned_by / order creator) ──
        manager = (
            User.objects.filter(profile__role="fleet_manager", is_active=True)
            .order_by("id")
            .first()
        )
        if not manager:
            self.stdout.write(self.style.ERROR(
                "No fleet manager found. Run `seed_data` first."
            ))
            return
        self.stdout.write(f"  Manager : {manager.username} (id={manager.id})")

        # ── 3. Find an available vehicle ───────────────────────────────
        vehicle = (
            Vehicle.objects.filter(status="available")
            .order_by("id")
            .first()
        )
        if not vehicle:
            # take any vehicle if none is 'available'
            vehicle = Vehicle.objects.order_by("id").first()
        if not vehicle:
            self.stdout.write(self.style.ERROR(
                "No vehicle found. Run `seed_data` first."
            ))
            return
        self.stdout.write(f"  Vehicle : {vehicle.registration_no} (id={vehicle.id})")

        # ── 4. Source warehouse Location ───────────────────────────────
        warehouse, _ = Location.objects.get_or_create(
            name="[DEMO] Hyderabad Central Depot",
            defaults={
                "address": "TSRTC Bus Depot, Hyderabad, Telangana 500038",
                "latitude": SOURCE_LAT,
                "longitude": SOURCE_LNG,
                "is_warehouse": True,
            },
        )
        self.stdout.write(f"  Warehouse: {warehouse.name} (id={warehouse.id})")

        # ── 5. Drop-point Locations ────────────────────────────────────
        drop_loc_1, _ = Location.objects.get_or_create(
            name="[DEMO] Bangalore Distribution Hub",
            defaults={
                "address": "MG Road, Bangalore, Karnataka 560001",
                "latitude": DROP1_LAT,
                "longitude": DROP1_LNG,
                "is_warehouse": False,
            },
        )
        drop_loc_2, _ = Location.objects.get_or_create(
            name="[DEMO] Chennai Regional Depot",
            defaults={
                "address": "Anna Salai, Chennai, Tamil Nadu 600002",
                "latitude": DROP2_LAT,
                "longitude": DROP2_LNG,
                "is_warehouse": False,
            },
        )
        self.stdout.write(f"  Drop 1  : {drop_loc_1.name} (id={drop_loc_1.id})")
        self.stdout.write(f"  Drop 2  : {drop_loc_2.name} (id={drop_loc_2.id})")

        # ── 6. Order ───────────────────────────────────────────────────
        order, created = Order.objects.get_or_create(
            order_ref=ORDER_REF,
            defaults={
                "created_by": manager,
                "warehouse": warehouse,
                "status": "assigned",
                "notes": "Demo order for UI testing – Hyderabad → Bangalore → Chennai",
            },
        )
        if not created:
            self.stdout.write(self.style.WARNING(
                f"  Order {ORDER_REF} already exists (id={order.id}). Skipping creation."
            ))
        else:
            self.stdout.write(f"  Order   : {ORDER_REF} (id={order.id})")

        # ── 7. Drop points on the order ────────────────────────────────
        dp1, _ = OrderDropPoint.objects.get_or_create(
            order=order,
            sequence_no=1,
            defaults={
                "location": drop_loc_1,
                "contact_name": "Ravi Kumar",
                "contact_phone": "+91-80-2345-6789",
                "notes": "Deliver before noon",
                "status": "pending",
            },
        )
        dp2, _ = OrderDropPoint.objects.get_or_create(
            order=order,
            sequence_no=2,
            defaults={
                "location": drop_loc_2,
                "contact_name": "Priya Nair",
                "contact_phone": "+91-44-9876-5432",
                "notes": "Call 30 minutes before arrival",
                "status": "pending",
            },
        )

        # ── 8. Trip ────────────────────────────────────────────────────
        trip = Trip.objects.filter(order=order).first()
        if not trip:
            trip = Trip.objects.create(
                order=order,
                vehicle=vehicle,
                driver=driver,
                assigned_by=manager,
                status="assigned",
                scheduled_start=timezone.now() + __import__("datetime").timedelta(hours=1),
            )
            self.stdout.write(f"  Trip    : id={trip.id} | driver={driver.username} | vehicle={vehicle.registration_no}")
        else:
            self.stdout.write(self.style.WARNING(
                f"  Trip already exists (id={trip.id}). Updating driver/vehicle."
            ))
            trip.driver  = driver
            trip.vehicle = vehicle
            trip.assigned_by = manager
            trip.save(update_fields=["driver", "vehicle", "assigned_by"])

        # ── 9. Route ───────────────────────────────────────────────────
        route, _ = Route.objects.get_or_create(
            trip=trip,
            defaults={
                "origin_lat": SOURCE_LAT,
                "origin_lng": SOURCE_LNG,
                "destination_lat": DROP2_LAT,
                "destination_lng": DROP2_LNG,
                "optimized_path": [
                    {"lat": float(SOURCE_LAT),  "lng": float(SOURCE_LNG)},
                    {"lat": 15.8280000,          "lng": 78.0370000},   # midpoint
                    {"lat": float(DROP1_LAT),   "lng": float(DROP1_LNG)},
                    {"lat": float(DROP2_LAT),   "lng": float(DROP2_LNG)},
                ],
                "total_distance_km": Decimal("1410.00"),
                "estimated_duration_min": 1300,
                "approved_by": manager,
                "approved_at": timezone.now(),
            },
        )

        # ── 10. DriverLocation (the money shot) ───────────────────────
        dl, dl_created = DriverLocation.objects.update_or_create(
            trip=trip,
            driver=driver,
            defaults={
                "vehicle": vehicle,
                "latitude": DRIVER_LAT,
                "longitude": DRIVER_LNG,
                "speed_kmh": Decimal("0.00"),
                "heading_deg": Decimal("45.00"),
            },
        )
        action = "Created" if dl_created else "Updated"
        self.stdout.write(self.style.SUCCESS(
            f"  DriverLocation: {action} (id={dl.id}) "
            f"lat={dl.latitude} lng={dl.longitude}"
        ))

        # ── Summary ────────────────────────────────────────────────────
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("=" * 60))
        self.stdout.write(self.style.SUCCESS("  DEMO TRIP SEEDED SUCCESSFULLY"))
        self.stdout.write(self.style.SUCCESS("=" * 60))
        self.stdout.write(f"  Login as driver : {driver.username} / Test@12345")
        self.stdout.write(f"  Trip ID         : {trip.id}")
        self.stdout.write(f"  Source (pickup) : Hyderabad ({SOURCE_LAT}, {SOURCE_LNG})")
        self.stdout.write(f"  Drop 1          : Bangalore ({DROP1_LAT}, {DROP1_LNG})")
        self.stdout.write(f"  Drop 2          : Chennai   ({DROP2_LAT}, {DROP2_LNG})")
        self.stdout.write(f"  Driver location : ({DRIVER_LAT}, {DRIVER_LNG})")
        self.stdout.write("")
        self.stdout.write("  Open the app → log in as the driver above")
        self.stdout.write("  → Dashboard → 'Start Trip'")
        self.stdout.write("  → The green 🟢 pin should appear on the Route Preview map")
        self.stdout.write(self.style.SUCCESS("=" * 60))

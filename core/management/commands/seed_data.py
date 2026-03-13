"""
Management command to seed the database with realistic dummy data.

Usage:
    python manage.py seed_data          # seed everything
    python manage.py seed_data --flush  # wipe app tables first, then seed
"""

import random
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from core.models import Geofence, Location, UserProfile
from fleet.models import (
    Inspection,
    InspectionChecklist,
    InspectionChecklistItem,
    InspectionResult,
    Vehicle,
    VehicleIssue,
)
from trips.models import (
    DeliveryProof,
    FuelLog,
    GeofenceEvent,
    GpsLog,
    Order,
    OrderDropPoint,
    Route,
    RouteDeviation,
    Trip,
    TripExpense,
)
from maintenance.models import MaintenanceRecord, MaintenanceSchedule, SparePartUsed
from comms.models import Message, Notification, SOSAlert

User = get_user_model()

# ── Helpers ──────────────────────────────────────────────────────────────────

NOW = timezone.now()


def _dt(days_ago=0, hours_ago=0):
    return NOW - timedelta(days=days_ago, hours=hours_ago)


def _dec(val):
    return Decimal(str(val))


def _coord():
    """Return a random lat/lng around Indian cities."""
    cities = [
        (19.0760, 72.8777),   # Mumbai
        (28.6139, 77.2090),   # Delhi
        (12.9716, 77.5946),   # Bangalore
        (13.0827, 80.2707),   # Chennai
        (22.5726, 88.3639),   # Kolkata
        (17.3850, 78.4867),   # Hyderabad
        (23.0225, 72.5714),   # Ahmedabad
        (18.5204, 73.8567),   # Pune
    ]
    lat, lng = random.choice(cities)
    lat += random.uniform(-0.05, 0.05)
    lng += random.uniform(-0.05, 0.05)
    return round(lat, 7), round(lng, 7)


# ── Data constants ───────────────────────────────────────────────────────────

DRIVER_NAMES = [
    ("Rahul", "Sharma"),
    ("Amit", "Verma"),
    ("Suresh", "Patel"),
    ("Vikram", "Singh"),
    ("Deepak", "Kumar"),
]

FM_NAMES = [
    ("Priya", "Desai"),
    ("Anita", "Nair"),
    ("Rajesh", "Gupta"),
    ("Sanjay", "Reddy"),
    ("Meena", "Joshi"),
]

MS_NAMES = [
    ("Kiran", "Rao"),
    ("Manoj", "Tiwari"),
    ("Anil", "Saxena"),
    ("Ravi", "Mishra"),
    ("Gaurav", "Yadav"),
]

VEHICLE_DATA = [
    ("MH12AB1234", "Tata", "Ace Gold", 2022, "diesel", 750),
    ("MH14CD5678", "Tata", "407", 2021, "diesel", 2500),
    ("DL01EF9012", "Ashok Leyland", "Dost", 2023, "diesel", 1500),
    ("KA03GH3456", "Mahindra", "Bolero Pickup", 2020, "diesel", 1200),
    ("TN07IJ7890", "Eicher", "Pro 2049", 2022, "diesel", 4000),
    ("GJ05KL2345", "BharatBenz", "1015R", 2023, "diesel", 6000),
    ("RJ14MN6789", "Tata", "Signa 1918", 2021, "diesel", 16000),
    ("UP32OP0123", "Ashok Leyland", "Partner", 2024, "cng", 1000),
    ("AP09QR4567", "Mahindra", "Furio 7", 2023, "diesel", 3500),
    ("MH04ST8901", "Tata", "Ultra 1012", 2022, "diesel", 5000),
    ("KA01UV2345", "Eicher", "Pro 3015", 2024, "diesel", 8000),
    ("DL10WX6789", "BharatBenz", "1217C", 2023, "diesel", 10000),
]

LOCATION_DATA = [
    ("Mumbai Central Warehouse", "Plot 45, MIDC, Andheri East, Mumbai", 19.1134, 72.8654, True),
    ("Delhi Hub", "Sector 18, Gurugram, Delhi NCR", 28.4595, 77.0266, True),
    ("Bangalore Distribution Center", "Peenya Industrial Area, Bangalore", 13.0358, 77.5229, True),
    ("Pune Warehouse", "Hinjewadi Phase 2, Pune", 18.5912, 73.7388, True),
    ("Chennai Depot", "Ambattur Industrial Estate, Chennai", 13.1067, 80.1569, True),
    # Drop-off locations
    ("Reliance Fresh - Bandra", "Hill Road, Bandra West, Mumbai", 19.0544, 72.8252, False),
    ("Big Bazaar - Connaught Place", "Block A, CP, New Delhi", 28.6315, 77.2167, False),
    ("Star Bazaar - Koramangala", "80 Feet Road, Koramangala, Bangalore", 12.9352, 77.6245, False),
    ("DMart - Wakad", "Near Hinjewadi Bridge, Wakad, Pune", 18.5985, 73.7605, False),
    ("Spencer's - T Nagar", "Usman Road, T Nagar, Chennai", 13.0418, 80.2341, False),
    ("More Supermarket - Salt Lake", "Sector V, Salt Lake, Kolkata", 22.5726, 88.4315, False),
    ("Ratnadeep - HITEC City", "Madhapur, Hyderabad", 17.4486, 78.3908, False),
    ("Easyday - SG Highway", "Near Bodakdev, Ahmedabad", 23.0395, 72.5113, False),
    ("Nature's Basket - Viman Nagar", "Opposite Lunkad Gold Coast, Pune", 18.5679, 73.9143, False),
    ("Spar - Adyar", "LB Road, Adyar, Chennai", 13.0062, 80.2574, False),
]

CHECKLIST_ITEMS = [
    "Engine oil level",
    "Coolant level",
    "Tire pressure (all wheels)",
    "Brake fluid level",
    "Windshield & mirrors condition",
    "Headlights & tail lights",
    "Horn",
    "Seat belts",
    "Fire extinguisher",
    "First aid kit",
    "Fuel level",
    "Battery condition",
]


class Command(BaseCommand):
    help = "Seed database with realistic dummy data"

    def add_arguments(self, parser):
        parser.add_argument(
            "--flush",
            action="store_true",
            help="Delete all existing app data before seeding",
        )

    def handle(self, *args, **options):
        if options["flush"]:
            self.stdout.write("Flushing existing data...")
            self._flush()

        self.stdout.write("Seeding database...")
        drivers = self._create_users(DRIVER_NAMES, "driver", "driver")
        fleet_mgrs = self._create_users(FM_NAMES, "fleet_manager", "fm")
        maint_staff = self._create_users(MS_NAMES, "maintenance_staff", "ms")
        all_users = drivers + fleet_mgrs + maint_staff

        locations = self._create_locations()
        warehouses = [l for l in locations if l.is_warehouse]
        drop_offs = [l for l in locations if not l.is_warehouse]
        geofences = self._create_geofences(locations, fleet_mgrs)
        vehicles = self._create_vehicles()
        checklists, items = self._create_checklists()

        orders = self._create_orders(fleet_mgrs, warehouses, drop_offs)
        trips = self._create_trips(orders, vehicles, drivers, fleet_mgrs)
        routes = self._create_routes(trips)
        self._create_gps_logs(trips, vehicles)
        self._create_route_deviations(trips)
        self._create_geofence_events(trips, vehicles, geofences)
        self._create_trip_expenses(trips, drivers)
        self._create_fuel_logs(trips, vehicles, drivers)
        self._create_delivery_proofs(trips, drivers)

        inspections = self._create_inspections(
            trips, vehicles, drivers, checklists, items, fleet_mgrs + maint_staff
        )
        issues = self._create_vehicle_issues(vehicles, drivers)

        schedules = self._create_maintenance_schedules(vehicles, maint_staff + fleet_mgrs)
        records = self._create_maintenance_records(
            vehicles, issues, schedules, maint_staff, fleet_mgrs
        )

        self._create_messages(drivers, fleet_mgrs, trips)
        self._create_notifications(all_users)
        self._create_sos_alerts(drivers, vehicles, trips, fleet_mgrs)

        self.stdout.write(self.style.SUCCESS("Database seeded successfully!"))

    # ── Flush ────────────────────────────────────────────────────────────────

    def _flush(self):
        SOSAlert.objects.all().delete()
        Notification.objects.all().delete()
        Message.objects.all().delete()
        SparePartUsed.objects.all().delete()
        MaintenanceRecord.objects.all().delete()
        MaintenanceSchedule.objects.all().delete()
        InspectionResult.objects.all().delete()
        Inspection.objects.all().delete()
        InspectionChecklistItem.objects.all().delete()
        InspectionChecklist.objects.all().delete()
        VehicleIssue.objects.all().delete()
        DeliveryProof.objects.all().delete()
        FuelLog.objects.all().delete()
        TripExpense.objects.all().delete()
        GeofenceEvent.objects.all().delete()
        GpsLog.objects.all().delete()
        RouteDeviation.objects.all().delete()
        Route.objects.all().delete()
        Trip.objects.all().delete()
        OrderDropPoint.objects.all().delete()
        Order.objects.all().delete()
        Vehicle.objects.all().delete()
        Geofence.objects.all().delete()
        Location.objects.all().delete()
        UserProfile.objects.all().delete()
        User.objects.filter(is_superuser=False).delete()
        self.stdout.write("  Flushed all app tables.")

    # ── Users ────────────────────────────────────────────────────────────────

    def _create_users(self, names, role, prefix):
        users = []
        for i, (first, last) in enumerate(names, 1):
            username = f"{prefix}_{first.lower()}"
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    "email": f"{username}@fleetdemo.com",
                    "first_name": first,
                    "last_name": last,
                },
            )
            if created:
                user.set_password("Test@12345")
                user.save()
            profile, _ = UserProfile.objects.get_or_create(user=user)
            profile.role = role
            profile.phone = f"+91-98765{random.randint(10000, 99999)}"
            profile.save()
            users.append(user)
        self.stdout.write(f"  Created {len(users)} {role}s")
        return users

    # ── Locations & Geofences ────────────────────────────────────────────────

    def _create_locations(self):
        locations = []
        for name, addr, lat, lng, is_wh in LOCATION_DATA:
            loc, _ = Location.objects.get_or_create(
                name=name,
                defaults={
                    "address": addr,
                    "latitude": _dec(lat),
                    "longitude": _dec(lng),
                    "is_warehouse": is_wh,
                },
            )
            locations.append(loc)
        self.stdout.write(f"  Created {len(locations)} locations")
        return locations

    def _create_geofences(self, locations, fleet_mgrs):
        geofences = []
        for loc in locations[:8]:  # geofences around first 8 locations
            gf, _ = Geofence.objects.get_or_create(
                name=f"{loc.name} Zone",
                defaults={
                    "location": loc,
                    "center_lat": loc.latitude,
                    "center_lng": loc.longitude,
                    "radius_meters": _dec(random.randint(300, 800)),
                    "created_by": random.choice(fleet_mgrs),
                },
            )
            geofences.append(gf)
        self.stdout.write(f"  Created {len(geofences)} geofences")
        return geofences

    # ── Vehicles ─────────────────────────────────────────────────────────────

    def _create_vehicles(self):
        vehicles = []
        for reg, make, model, year, fuel, cap in VEHICLE_DATA:
            v, _ = Vehicle.objects.get_or_create(
                registration_no=reg,
                defaults={
                    "make": make,
                    "model": model,
                    "year": year,
                    "fuel_type": fuel,
                    "capacity_kg": _dec(cap),
                    "status": "available",
                    "current_mileage_km": _dec(random.randint(5000, 80000)),
                    "last_service_date": (_dt(days_ago=random.randint(10, 90))).date(),
                    "next_service_due_date": (_dt(days_ago=-random.randint(30, 120))).date(),
                    "next_service_due_km": _dec(random.randint(20000, 100000)),
                },
            )
            vehicles.append(v)
        self.stdout.write(f"  Created {len(vehicles)} vehicles")
        return vehicles

    # ── Checklists ───────────────────────────────────────────────────────────

    def _create_checklists(self):
        cl, _ = InspectionChecklist.objects.get_or_create(
            name="Standard Pre/Post Trip Checklist"
        )
        items = []
        for i, item_name in enumerate(CHECKLIST_ITEMS, 1):
            item, _ = InspectionChecklistItem.objects.get_or_create(
                checklist=cl,
                item_name=item_name,
                defaults={"sequence_no": i, "is_required": True},
            )
            items.append(item)
        self.stdout.write(f"  Created 1 checklist with {len(items)} items")
        return [cl], items

    # ── Orders & Drop Points ─────────────────────────────────────────────────

    def _create_orders(self, fleet_mgrs, warehouses, drop_offs):
        orders = []
        statuses = ["pending", "assigned", "in_transit", "delivered", "delivered",
                     "delivered", "failed", "assigned", "in_transit", "pending"]
        for i in range(10):
            ref = f"ORD-2026-{1000 + i}"
            order, created = Order.objects.get_or_create(
                order_ref=ref,
                defaults={
                    "created_by": random.choice(fleet_mgrs),
                    "warehouse": random.choice(warehouses),
                    "status": statuses[i],
                    "notes": f"Order {ref} – {'Priority' if i % 3 == 0 else 'Standard'} delivery",
                },
            )
            if created:
                # 2-4 drop points per order
                num_drops = random.randint(2, 4)
                chosen = random.sample(drop_offs, min(num_drops, len(drop_offs)))
                for seq, loc in enumerate(chosen, 1):
                    OrderDropPoint.objects.create(
                        order=order,
                        location=loc,
                        sequence_no=seq,
                        contact_name=f"Contact {seq}",
                        contact_phone=f"+91-98{random.randint(10000000, 99999999)}",
                        notes=f"Drop {seq} for {ref}",
                        status="delivered" if order.status == "delivered" else "pending",
                    )
            orders.append(order)
        self.stdout.write(f"  Created {len(orders)} orders with drop points")
        return orders

    # ── Trips ────────────────────────────────────────────────────────────────

    def _create_trips(self, orders, vehicles, drivers, fleet_mgrs):
        trips = []
        for i, order in enumerate(orders):
            vehicle = vehicles[i % len(vehicles)]
            driver = drivers[i % len(drivers)]

            if order.status == "pending":
                trip_status = "assigned"
            elif order.status == "assigned":
                trip_status = "assigned"
            elif order.status == "in_transit":
                trip_status = "in_progress"
            elif order.status == "delivered":
                trip_status = "completed"
            else:
                trip_status = "cancelled"

            days_ago = random.randint(1, 30)
            start_km = float(vehicle.current_mileage_km) - random.randint(50, 500)

            trip, created = Trip.objects.get_or_create(
                order=order,
                vehicle=vehicle,
                driver=driver,
                defaults={
                    "assigned_by": random.choice(fleet_mgrs),
                    "status": trip_status,
                    "start_mileage_km": _dec(max(start_km, 0)),
                    "end_mileage_km": vehicle.current_mileage_km if trip_status == "completed" else None,
                    "scheduled_start": _dt(days_ago=days_ago, hours_ago=2),
                    "started_at": _dt(days_ago=days_ago) if trip_status in ("in_progress", "completed") else None,
                    "ended_at": _dt(days_ago=days_ago - 1) if trip_status == "completed" else None,
                    "start_location_lat": _dec(_coord()[0]) if trip_status in ("in_progress", "completed") else None,
                    "start_location_lng": _dec(_coord()[1]) if trip_status in ("in_progress", "completed") else None,
                    "end_location_lat": _dec(_coord()[0]) if trip_status == "completed" else None,
                    "end_location_lng": _dec(_coord()[1]) if trip_status == "completed" else None,
                },
            )
            trips.append(trip)
        self.stdout.write(f"  Created {len(trips)} trips")
        return trips

    # ── Routes ───────────────────────────────────────────────────────────────

    def _create_routes(self, trips):
        routes = []
        for trip in trips:
            if hasattr(trip, "route_detail"):
                try:
                    trip.route_detail  # noqa
                    routes.append(trip.route_detail)
                    continue
                except Route.DoesNotExist:
                    pass
            o_lat, o_lng = _coord()
            d_lat, d_lng = _coord()
            route = Route.objects.create(
                trip=trip,
                origin_lat=_dec(o_lat),
                origin_lng=_dec(o_lng),
                destination_lat=_dec(d_lat),
                destination_lng=_dec(d_lng),
                total_distance_km=_dec(random.randint(50, 600)),
                estimated_duration_min=random.randint(60, 720),
                optimized_path=[
                    {"lat": o_lat, "lng": o_lng},
                    {"lat": (o_lat + d_lat) / 2, "lng": (o_lng + d_lng) / 2},
                    {"lat": d_lat, "lng": d_lng},
                ],
            )
            routes.append(route)
        self.stdout.write(f"  Created {len(routes)} routes")
        return routes

    # ── GPS Logs ─────────────────────────────────────────────────────────────

    def _create_gps_logs(self, trips, vehicles):
        count = 0
        for trip in trips:
            if trip.status in ("in_progress", "completed"):
                vehicle = trip.vehicle
                base_lat, base_lng = _coord()
                num_logs = random.randint(15, 40)
                for j in range(num_logs):
                    GpsLog.objects.create(
                        trip=trip,
                        vehicle=vehicle,
                        latitude=_dec(base_lat + j * 0.002 + random.uniform(-0.001, 0.001)),
                        longitude=_dec(base_lng + j * 0.003 + random.uniform(-0.001, 0.001)),
                        speed_kmh=_dec(random.uniform(0, 80)),
                        heading_deg=_dec(random.uniform(0, 360)),
                    )
                    count += 1
        self.stdout.write(f"  Created {count} GPS logs")

    # ── Route Deviations ─────────────────────────────────────────────────────

    def _create_route_deviations(self, trips):
        count = 0
        for trip in trips:
            if trip.status in ("in_progress", "completed") and random.random() < 0.4:
                for _ in range(random.randint(1, 3)):
                    lat, lng = _coord()
                    RouteDeviation.objects.create(
                        trip=trip,
                        latitude=_dec(lat),
                        longitude=_dec(lng),
                        deviation_meters=_dec(random.randint(100, 2000)),
                        resolved_at=_dt(days_ago=random.randint(0, 5)) if random.random() < 0.6 else None,
                    )
                    count += 1
        self.stdout.write(f"  Created {count} route deviations")

    # ── Geofence Events ──────────────────────────────────────────────────────

    def _create_geofence_events(self, trips, vehicles, geofences):
        count = 0
        for trip in trips:
            if trip.status in ("in_progress", "completed") and geofences:
                for _ in range(random.randint(1, 4)):
                    lat, lng = _coord()
                    GeofenceEvent.objects.create(
                        trip=trip,
                        vehicle=trip.vehicle,
                        geofence=random.choice(geofences),
                        event_type=random.choice(["entry", "exit"]),
                        latitude=_dec(lat),
                        longitude=_dec(lng),
                    )
                    count += 1
        self.stdout.write(f"  Created {count} geofence events")

    # ── Trip Expenses ────────────────────────────────────────────────────────

    def _create_trip_expenses(self, trips, drivers):
        count = 0
        expense_types = ["fuel", "toll", "parking", "other"]
        for trip in trips:
            if trip.status in ("in_progress", "completed"):
                for _ in range(random.randint(1, 4)):
                    TripExpense.objects.create(
                        trip=trip,
                        driver=trip.driver,
                        expense_type=random.choice(expense_types),
                        amount=_dec(random.randint(50, 5000)),
                        currency="INR",
                        description=f"Expense during trip #{trip.pk}",
                    )
                    count += 1
        self.stdout.write(f"  Created {count} trip expenses")

    # ── Fuel Logs ────────────────────────────────────────────────────────────

    def _create_fuel_logs(self, trips, vehicles, drivers):
        count = 0
        stations = [
            "HP Petrol Pump - Highway NH4",
            "Indian Oil - Wakad",
            "Bharat Petroleum - Ring Road",
            "Shell Fuel Station - Outer Ring",
            "Reliance Petrol Pump - Bypass",
        ]
        for trip in trips:
            if trip.status in ("in_progress", "completed"):
                liters = _dec(random.randint(20, 80))
                cost_per = _dec(round(random.uniform(90, 110), 2))
                FuelLog.objects.create(
                    trip=trip,
                    vehicle=trip.vehicle,
                    driver=trip.driver,
                    fuel_amount_liters=liters,
                    cost_per_liter=cost_per,
                    total_cost=liters * cost_per,
                    odometer_km=trip.start_mileage_km + _dec(random.randint(10, 200)) if trip.start_mileage_km else _dec(10000),
                    fuel_station=random.choice(stations),
                )
                count += 1
        self.stdout.write(f"  Created {count} fuel logs")

    # ── Delivery Proofs ──────────────────────────────────────────────────────

    def _create_delivery_proofs(self, trips, drivers):
        count = 0
        for trip in trips:
            if trip.status == "completed":
                drop_points = trip.order.drop_points.all()
                for dp in drop_points:
                    lat, lng = _coord()
                    DeliveryProof.objects.create(
                        drop_point=dp,
                        trip=trip,
                        driver=trip.driver,
                        proof_type=random.choice(["photo", "signature", "digital_confirmation"]),
                        digital_confirmation_code=f"CONF-{random.randint(10000, 99999)}",
                        latitude=_dec(lat),
                        longitude=_dec(lng),
                    )
                    count += 1
        self.stdout.write(f"  Created {count} delivery proofs")

    # ── Inspections ──────────────────────────────────────────────────────────

    def _create_inspections(self, trips, vehicles, drivers, checklists, items, reviewers):
        inspections = []
        for trip in trips:
            for insp_type in ["pre_trip", "post_trip"]:
                if insp_type == "post_trip" and trip.status != "completed":
                    continue
                status = random.choice(["approved", "approved", "flagged", "pending"])
                insp = Inspection.objects.create(
                    trip=trip,
                    vehicle=trip.vehicle,
                    driver=trip.driver,
                    checklist=checklists[0],
                    inspection_type=insp_type,
                    overall_status=status,
                    notes=f"{insp_type.replace('_', ' ').title()} inspection for Trip #{trip.pk}",
                    reviewed_by=random.choice(reviewers) if status != "pending" else None,
                    reviewed_at=_dt(days_ago=random.randint(0, 5)) if status != "pending" else None,
                )
                # Create results for each checklist item
                for item in items:
                    InspectionResult.objects.create(
                        inspection=insp,
                        checklist_item=item,
                        result=random.choices(["pass", "fail", "na"], weights=[80, 15, 5])[0],
                        notes="" if random.random() > 0.3 else "Needs attention",
                    )
                inspections.append(insp)
        self.stdout.write(f"  Created {len(inspections)} inspections with results")
        return inspections

    # ── Vehicle Issues ───────────────────────────────────────────────────────

    def _create_vehicle_issues(self, vehicles, drivers):
        issues = []
        issue_titles = [
            ("Brake pads worn", "high"),
            ("Engine oil leak", "critical"),
            ("Left headlight dim", "low"),
            ("Tire tread below minimum", "medium"),
            ("AC not cooling", "low"),
            ("Suspension noise on bumps", "medium"),
            ("Windshield crack", "medium"),
            ("Exhaust smoke excessive", "high"),
            ("Battery draining fast", "medium"),
            ("Steering wheel vibration", "high"),
            ("Clutch slipping", "critical"),
            ("Door lock malfunction", "low"),
        ]
        statuses = ["reported", "acknowledged", "in_repair", "resolved"]
        for vehicle in vehicles:
            num_issues = random.randint(1, 3)
            chosen = random.sample(issue_titles, num_issues)
            for title, severity in chosen:
                issue = VehicleIssue.objects.create(
                    vehicle=vehicle,
                    reported_by=random.choice(drivers),
                    title=f"{title} – {vehicle.registration_no}",
                    description=f"{title} detected on {vehicle.make} {vehicle.model} ({vehicle.registration_no})",
                    severity=severity,
                    status=random.choice(statuses),
                )
                issues.append(issue)
        self.stdout.write(f"  Created {len(issues)} vehicle issues")
        return issues

    # ── Maintenance Schedules ────────────────────────────────────────────────

    def _create_maintenance_schedules(self, vehicles, staff):
        schedules = []
        maint_types = ["preventive", "corrective", "emergency"]
        schedule_statuses = ["scheduled", "in_progress", "completed", "cancelled"]
        descriptions = [
            "Regular 10K km service",
            "Brake system overhaul",
            "Transmission fluid change",
            "Full vehicle inspection",
            "Electrical system check",
            "Tire rotation and alignment",
        ]
        for vehicle in vehicles:
            num = random.randint(1, 3)
            for _ in range(num):
                sched = MaintenanceSchedule.objects.create(
                    vehicle=vehicle,
                    scheduled_by=random.choice(staff),
                    maintenance_type=random.choice(maint_types),
                    description=random.choice(descriptions),
                    scheduled_date=(_dt(days_ago=random.randint(-30, 60))).date(),
                    estimated_duration_hours=_dec(random.choice([2, 4, 6, 8])),
                    status=random.choice(schedule_statuses),
                    notes=f"Scheduled maintenance for {vehicle.registration_no}",
                )
                schedules.append(sched)
        self.stdout.write(f"  Created {len(schedules)} maintenance schedules")
        return schedules

    # ── Maintenance Records ──────────────────────────────────────────────────

    def _create_maintenance_records(self, vehicles, issues, schedules, maint_staff, fleet_mgrs):
        records = []
        spare_parts_data = [
            ("Oil Filter", "OF-001", 250),
            ("Air Filter", "AF-002", 450),
            ("Brake Pad Set", "BP-003", 1500),
            ("Spark Plug (set of 4)", "SP-004", 800),
            ("Clutch Plate", "CP-005", 3500),
            ("Fan Belt", "FB-006", 600),
            ("Wiper Blades", "WB-007", 350),
            ("Coolant (5L)", "CL-008", 500),
            ("Brake Fluid (1L)", "BF-009", 300),
            ("Engine Oil (5L)", "EO-010", 1200),
        ]

        completed_schedules = [s for s in schedules if s.status == "completed"]
        resolved_issues = [i for i in issues if i.status == "resolved"]

        # Records linked to schedules
        for sched in completed_schedules[:8]:
            record = MaintenanceRecord.objects.create(
                vehicle=sched.vehicle,
                schedule=sched,
                maintenance_type=sched.maintenance_type,
                description=sched.description,
                repair_status="completed",
                assigned_to=random.choice(maint_staff),
                assigned_by=random.choice(fleet_mgrs),
                started_at=_dt(days_ago=random.randint(2, 20)),
                completed_at=_dt(days_ago=random.randint(0, 2)),
                total_cost=_dec(random.randint(500, 15000)),
                mileage_at_service=sched.vehicle.current_mileage_km,
                technician_notes="Service completed successfully. All parts replaced.",
            )
            # Add spare parts
            for _ in range(random.randint(1, 4)):
                part = random.choice(spare_parts_data)
                qty = _dec(random.randint(1, 3))
                unit_cost = _dec(part[2])
                SparePartUsed.objects.create(
                    maintenance=record,
                    part_name=part[0],
                    part_number=part[1],
                    quantity=qty,
                    unit_cost=unit_cost,
                    total_cost=qty * unit_cost,
                )
            records.append(record)

        # Records linked to issues
        for issue in resolved_issues[:5]:
            record = MaintenanceRecord.objects.create(
                vehicle=issue.vehicle,
                issue=issue,
                maintenance_type="corrective",
                description=f"Fix: {issue.title}",
                repair_status="completed",
                assigned_to=random.choice(maint_staff),
                assigned_by=random.choice(fleet_mgrs),
                started_at=_dt(days_ago=random.randint(2, 15)),
                completed_at=_dt(days_ago=random.randint(0, 2)),
                total_cost=_dec(random.randint(1000, 20000)),
                mileage_at_service=issue.vehicle.current_mileage_km,
                technician_notes=f"Resolved issue: {issue.title}",
            )
            for _ in range(random.randint(1, 3)):
                part = random.choice(spare_parts_data)
                qty = _dec(random.randint(1, 2))
                unit_cost = _dec(part[2])
                SparePartUsed.objects.create(
                    maintenance=record,
                    part_name=part[0],
                    part_number=part[1],
                    quantity=qty,
                    unit_cost=unit_cost,
                    total_cost=qty * unit_cost,
                )
            records.append(record)

        # A couple of in-progress records
        for vehicle in vehicles[:3]:
            record = MaintenanceRecord.objects.create(
                vehicle=vehicle,
                maintenance_type=random.choice(["preventive", "corrective"]),
                description="Ongoing maintenance",
                repair_status="in_progress",
                assigned_to=random.choice(maint_staff),
                assigned_by=random.choice(fleet_mgrs),
                started_at=_dt(days_ago=1),
                mileage_at_service=vehicle.current_mileage_km,
                technician_notes="Work in progress",
            )
            records.append(record)

        self.stdout.write(f"  Created {len(records)} maintenance records with spare parts")
        return records

    # ── Messages ─────────────────────────────────────────────────────────────

    def _create_messages(self, drivers, fleet_mgrs, trips):
        count = 0
        messages_text = [
            "Loading complete, departing now.",
            "Stuck in traffic near toll plaza. ETA delayed by 30 min.",
            "Reached drop point 1. Unloading.",
            "Vehicle making unusual noise. Please advise.",
            "All deliveries complete. Heading back.",
            "Please confirm the warehouse gate timing.",
            "Route diverted due to road block on NH4.",
            "Need fuel reimbursement approval.",
            "Customer not available at drop point. Waiting.",
            "Inspection done. Minor issue with left headlight.",
            "Great job on today's deliveries!",
            "Please submit your trip expense report.",
            "Your next trip is assigned for tomorrow 6 AM.",
            "Maintenance done. Vehicle cleared for trips.",
            "Sending GPS logs for review.",
        ]
        active_trips = [t for t in trips if t.status in ("in_progress", "completed")]
        for _ in range(25):
            sender = random.choice(drivers + fleet_mgrs)
            receiver = random.choice(fleet_mgrs if sender in drivers else drivers)
            while receiver == sender:
                receiver = random.choice(drivers + fleet_mgrs)
            is_read = random.random() < 0.6
            msg = Message.objects.create(
                sender=sender,
                receiver=receiver,
                trip=random.choice(active_trips) if active_trips and random.random() < 0.7 else None,
                content=random.choice(messages_text),
                is_read=is_read,
                read_at=_dt(days_ago=random.randint(0, 3)) if is_read else None,
            )
            count += 1
        self.stdout.write(f"  Created {count} messages")

    # ── Notifications ────────────────────────────────────────────────────────

    def _create_notifications(self, all_users):
        count = 0
        alert_types = ["sos", "route_deviation", "geofence_entry", "geofence_exit",
                        "maintenance_due", "issue_reported"]
        titles = {
            "sos": "SOS Alert triggered by driver",
            "route_deviation": "Route deviation detected on Trip",
            "geofence_entry": "Vehicle entered geofence zone",
            "geofence_exit": "Vehicle exited geofence zone",
            "maintenance_due": "Vehicle maintenance is due",
            "issue_reported": "New vehicle issue reported",
        }
        for _ in range(30):
            alert = random.choice(alert_types)
            status = random.choice(["unread", "unread", "read"])
            Notification.objects.create(
                user=random.choice(all_users),
                alert_type=alert,
                title=titles[alert],
                body=f"Automated notification: {titles[alert]}. Please check the dashboard.",
                status=status,
                reference_id=random.randint(1, 20),
                reference_type=random.choice(["trip", "vehicle", "order"]),
                read_at=_dt(days_ago=random.randint(0, 5)) if status == "read" else None,
            )
            count += 1
        self.stdout.write(f"  Created {count} notifications")

    # ── SOS Alerts ───────────────────────────────────────────────────────────

    def _create_sos_alerts(self, drivers, vehicles, trips, fleet_mgrs):
        count = 0
        sos_messages = [
            "Accident on highway, need immediate help!",
            "Vehicle breakdown, stranded on the road.",
            "Flat tire on an isolated stretch.",
            "Health emergency – driver feeling unwell.",
            "Suspicious activity near the vehicle.",
        ]
        active_trips = [t for t in trips if t.status in ("in_progress", "completed")]
        for i in range(5):
            lat, lng = _coord()
            resolved = random.random() < 0.6
            SOSAlert.objects.create(
                driver=drivers[i % len(drivers)],
                vehicle=vehicles[i % len(vehicles)],
                trip=active_trips[i % len(active_trips)] if active_trips else None,
                latitude=_dec(lat),
                longitude=_dec(lng),
                message=sos_messages[i],
                resolved=resolved,
                resolved_by=random.choice(fleet_mgrs) if resolved else None,
                resolved_at=_dt(days_ago=random.randint(0, 3)) if resolved else None,
            )
            count += 1
        self.stdout.write(f"  Created {count} SOS alerts")

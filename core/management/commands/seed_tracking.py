"""
Seed realistic live-tracking data for in_progress trips.

Creates:
  - Ensures at least 3 trips are in_progress with proper routes
  - Realistic GPS trails that follow the planned route path
  - DriverLocation entries (current position snapshot)
  - Route with detailed optimized_path (many waypoints)

Usage:
    python manage.py seed_tracking          # add tracking data
    python manage.py seed_tracking --reset  # clear old tracking data first
"""

import math
import random
from decimal import Decimal
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from core.models import Location, UserProfile
from fleet.models import Vehicle
from trips.models import (
    DriverLocation,
    GpsLog,
    Order,
    OrderDropPoint,
    Route,
    Trip,
)

User = get_user_model()
NOW = timezone.now()


def _dec(val):
    return Decimal(str(round(val, 7)))


def _lerp(a, b, t):
    """Linear interpolation between two values."""
    return a + (b - a) * t


def _interpolate_path(waypoints, num_points):
    """
    Given a list of (lat, lng) waypoints, produce num_points evenly
    distributed along the path with slight realistic jitter.
    """
    if len(waypoints) < 2:
        return waypoints

    # Calculate segment lengths
    segments = []
    total_length = 0.0
    for i in range(len(waypoints) - 1):
        dx = waypoints[i + 1][0] - waypoints[i][0]
        dy = waypoints[i + 1][1] - waypoints[i][1]
        seg_len = math.sqrt(dx * dx + dy * dy)
        segments.append(seg_len)
        total_length += seg_len

    if total_length == 0:
        return waypoints

    points = []
    for p in range(num_points):
        t = p / max(num_points - 1, 1)
        target_dist = t * total_length

        # Find which segment this falls in
        cum_dist = 0.0
        for i, seg_len in enumerate(segments):
            if cum_dist + seg_len >= target_dist or i == len(segments) - 1:
                seg_t = (target_dist - cum_dist) / seg_len if seg_len > 0 else 0
                lat = _lerp(waypoints[i][0], waypoints[i + 1][0], seg_t)
                lng = _lerp(waypoints[i][1], waypoints[i + 1][1], seg_t)
                # Add slight jitter for realism (road curves)
                lat += random.uniform(-0.0003, 0.0003)
                lng += random.uniform(-0.0003, 0.0003)
                points.append((round(lat, 7), round(lng, 7)))
                break
            cum_dist += seg_len

    return points


# ── Realistic route data (Indian cities) ─────────────────────────────────────

ROUTES = [
    {
        "name": "Mumbai → Pune Express Delivery",
        "order_ref": "ORD-TRACK-001",
        "warehouse": ("Mumbai Central Warehouse", "Plot 45, MIDC, Andheri East, Mumbai", 19.1134, 72.8654),
        "destinations": [
            ("Hinjewadi IT Park", "Phase 1, Hinjewadi, Pune", 18.5912, 73.7388),
            ("Wakad Drop Point", "Near Dange Chowk, Wakad, Pune", 18.5985, 73.7605),
        ],
        "waypoints": [
            (19.1134, 72.8654),   # Mumbai warehouse
            (19.0760, 72.8777),   # Mumbai central
            (19.0330, 72.8550),   # Sion
            (18.9900, 72.8400),   # Chembur
            (18.9500, 72.8900),   # Vashi
            (18.8600, 73.0200),   # Panvel
            (18.7800, 73.1500),   # Khopoli
            (18.7400, 73.2800),   # Lonavala approach
            (18.7200, 73.4000),   # Lonavala
            (18.6800, 73.5200),   # Talegaon
            (18.6300, 73.6500),   # Dehu Road
            (18.5912, 73.7388),   # Hinjewadi
            (18.5985, 73.7605),   # Wakad
        ],
        "progress": 0.65,  # Driver is 65% through the route
    },
    {
        "name": "Delhi → Jaipur Highway Run",
        "order_ref": "ORD-TRACK-002",
        "warehouse": ("Delhi Logistics Hub", "Sector 18, Gurugram, NCR", 28.4595, 77.0266),
        "destinations": [
            ("Jaipur Distribution Center", "Sitapura Industrial Area, Jaipur", 26.8500, 75.8400),
            ("Mansarovar Drop Off", "Mansarovar, Jaipur", 26.8800, 75.7600),
        ],
        "waypoints": [
            (28.4595, 77.0266),   # Gurugram
            (28.4200, 76.9800),   # Manesar
            (28.3800, 76.9200),   # Dharuhera
            (28.2500, 76.8200),   # Rewari
            (28.1000, 76.6500),   # Narnaul approach
            (27.9500, 76.4800),   # Behror
            (27.7500, 76.3200),   # Kotputli
            (27.5500, 76.2000),   # Shahpura
            (27.3500, 76.0500),   # Chomu
            (27.1500, 75.9500),   # Jaipur outskirts
            (26.9500, 75.8800),   # Tonk Road
            (26.8800, 75.7600),   # Mansarovar
            (26.8500, 75.8400),   # Sitapura
        ],
        "progress": 0.40,  # 40% through
    },
    {
        "name": "Bangalore → Chennai Express",
        "order_ref": "ORD-TRACK-003",
        "warehouse": ("Bangalore DC", "Peenya Industrial Area, Bangalore", 13.0358, 77.5229),
        "destinations": [
            ("Chennai Central Hub", "Ambattur Industrial Estate, Chennai", 13.1067, 80.1569),
            ("T Nagar Retail Drop", "Usman Road, T Nagar, Chennai", 13.0418, 80.2341),
        ],
        "waypoints": [
            (13.0358, 77.5229),   # Peenya
            (13.0200, 77.6200),   # Bangalore East
            (12.9800, 77.7500),   # Whitefield
            (12.9300, 77.9000),   # Hoskote
            (12.9500, 78.1200),   # Kolar
            (12.9200, 78.4000),   # Mulbagal
            (12.8500, 78.7000),   # Vaniyambadi
            (12.8000, 79.0000),   # Ambur
            (12.7500, 79.3000),   # Vellore
            (12.8000, 79.6000),   # Ranipet
            (12.8500, 79.9000),   # Kanchipuram
            (13.0000, 80.0500),   # Sriperumbudur
            (13.1067, 80.1569),   # Ambattur
            (13.0418, 80.2341),   # T Nagar
        ],
        "progress": 0.80,  # 80% through
    },
    {
        "name": "Hyderabad → Vijayawada Run",
        "order_ref": "ORD-TRACK-004",
        "warehouse": ("Hyderabad Warehouse", "Shamshabad, Hyderabad", 17.2400, 78.4300),
        "destinations": [
            ("Vijayawada Hub", "Auto Nagar, Vijayawada", 16.5062, 80.6480),
        ],
        "waypoints": [
            (17.2400, 78.4300),   # Shamshabad
            (17.1500, 78.5500),   # Ibrahimpatnam
            (17.0000, 78.8000),   # Nalgonda
            (16.8500, 79.1000),   # Miryalaguda
            (16.7000, 79.4000),   # Huzurnagar
            (16.5500, 79.7000),   # Jaggaiahpet
            (16.5200, 80.1000),   # Nandigama
            (16.5062, 80.6480),   # Vijayawada
        ],
        "progress": 0.55,
    },
]


class Command(BaseCommand):
    help = "Seed realistic live-tracking data (GPS trails, driver locations, routes)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Clear existing GPS logs, driver locations, and related route data before seeding",
        )

    def handle(self, *args, **options):
        if options["reset"]:
            self.stdout.write("Resetting tracking data...")
            DriverLocation.objects.all().delete()
            GpsLog.objects.all().delete()
            self.stdout.write("  Cleared GPS logs and driver locations.")

        # Get or verify prerequisite data
        drivers = list(User.objects.filter(profile__role="driver")[:5])
        fleet_mgrs = list(User.objects.filter(profile__role="fleet_manager")[:5])
        vehicles = list(Vehicle.objects.all()[:5])

        if not drivers or not fleet_mgrs or not vehicles:
            self.stderr.write(
                self.style.ERROR(
                    "No drivers/fleet managers/vehicles found. Run `python manage.py seed_data` first."
                )
            )
            return

        self.stdout.write(f"  Found {len(drivers)} drivers, {len(fleet_mgrs)} managers, {len(vehicles)} vehicles")

        for i, route_data in enumerate(ROUTES):
            driver = drivers[i % len(drivers)]
            manager = fleet_mgrs[i % len(fleet_mgrs)]
            vehicle = vehicles[i % len(vehicles)]

            self.stdout.write(f"\n  ── {route_data['name']} ──")

            # 1. Create or get locations
            wh_data = route_data["warehouse"]
            warehouse, _ = Location.objects.get_or_create(
                name=wh_data[0],
                defaults={
                    "address": wh_data[1],
                    "latitude": _dec(wh_data[2]),
                    "longitude": _dec(wh_data[3]),
                    "is_warehouse": True,
                },
            )

            dest_locations = []
            for dname, daddr, dlat, dlng in route_data["destinations"]:
                loc, _ = Location.objects.get_or_create(
                    name=dname,
                    defaults={
                        "address": daddr,
                        "latitude": _dec(dlat),
                        "longitude": _dec(dlng),
                        "is_warehouse": False,
                    },
                )
                dest_locations.append(loc)

            # 2. Create order
            order, _ = Order.objects.get_or_create(
                order_ref=route_data["order_ref"],
                defaults={
                    "created_by": manager,
                    "warehouse": warehouse,
                    "status": "in_transit",
                    "notes": route_data["name"],
                },
            )
            # Ensure status is in_transit
            if order.status != "in_transit":
                order.status = "in_transit"
                order.save()

            # 3. Create drop points
            for seq, loc in enumerate(dest_locations, 1):
                OrderDropPoint.objects.get_or_create(
                    order=order,
                    sequence_no=seq,
                    defaults={
                        "location": loc,
                        "contact_name": f"Contact {seq}",
                        "contact_phone": f"+91-98{random.randint(10000000, 99999999)}",
                        "notes": f"Drop {seq} – {loc.name}",
                        "status": "pending",
                    },
                )

            # 4. Create trip (in_progress)
            trip, trip_created = Trip.objects.get_or_create(
                order=order,
                defaults={
                    "vehicle": vehicle,
                    "driver": driver,
                    "assigned_by": manager,
                    "status": "in_progress",
                    "start_mileage_km": _dec(random.randint(15000, 50000)),
                    "scheduled_start": NOW - timedelta(hours=random.randint(2, 6)),
                    "started_at": NOW - timedelta(hours=random.randint(1, 4)),
                    "start_location_lat": _dec(route_data["waypoints"][0][0]),
                    "start_location_lng": _dec(route_data["waypoints"][0][1]),
                },
            )
            # Ensure trip is in_progress
            if trip.status != "in_progress":
                trip.status = "in_progress"
                trip.vehicle = vehicle
                trip.driver = driver
                trip.assigned_by = manager
                trip.started_at = NOW - timedelta(hours=random.randint(1, 4))
                trip.start_location_lat = _dec(route_data["waypoints"][0][0])
                trip.start_location_lng = _dec(route_data["waypoints"][0][1])
                trip.save()

            # Also set vehicle and driver status
            vehicle.status = "in_trip"
            vehicle.save()
            try:
                driver.profile.driver_status = "in_trip"
                driver.profile.save()
            except UserProfile.DoesNotExist:
                pass

            self.stdout.write(f"    Trip #{trip.id} — {driver.first_name} in {vehicle.registration_no}")

            # 5. Create detailed route with many waypoints
            waypoints = route_data["waypoints"]
            # Interpolate to get 20-30 waypoints for a smooth path
            detailed_path = _interpolate_path(waypoints, 25)
            optimized_path = [{"lat": lat, "lng": lng} for lat, lng in detailed_path]

            origin = waypoints[0]
            destination = waypoints[-1]
            total_km = random.randint(150, 600)
            duration_min = int(total_km * random.uniform(1.2, 1.8))

            try:
                route_obj = Route.objects.get(trip=trip)
            except Route.DoesNotExist:
                route_obj = None

            if route_obj:
                route_obj.origin_lat = _dec(origin[0])
                route_obj.origin_lng = _dec(origin[1])
                route_obj.destination_lat = _dec(destination[0])
                route_obj.destination_lng = _dec(destination[1])
                route_obj.optimized_path = optimized_path
                route_obj.total_distance_km = _dec(total_km)
                route_obj.estimated_duration_min = duration_min
                route_obj.save()
            else:
                route_obj = Route.objects.create(
                    trip=trip,
                    origin_lat=_dec(origin[0]),
                    origin_lng=_dec(origin[1]),
                    destination_lat=_dec(destination[0]),
                    destination_lng=_dec(destination[1]),
                    optimized_path=optimized_path,
                    total_distance_km=_dec(total_km),
                    estimated_duration_min=duration_min,
                )

            self.stdout.write(f"    Route: {len(optimized_path)} waypoints, {total_km} km, ~{duration_min} min")

            # 6. Create GPS trail (driver has traveled `progress` % of the route)
            progress = route_data["progress"]
            total_trail_points = int(len(detailed_path) * progress)
            trail_points = detailed_path[:max(total_trail_points, 3)]

            # Expand trail to many GPS pings (every ~30s of driving)
            expanded_trail = _interpolate_path(trail_points, random.randint(30, 60))

            # Clear old GPS logs for this trip if resetting
            if options["reset"]:
                GpsLog.objects.filter(trip=trip).delete()

            base_time = NOW - timedelta(hours=random.randint(1, 3))
            for j, (lat, lng) in enumerate(expanded_trail):
                GpsLog.objects.create(
                    trip=trip,
                    vehicle=vehicle,
                    latitude=_dec(lat),
                    longitude=_dec(lng),
                    speed_kmh=_dec(random.uniform(30, 80) if j > 0 else 0),
                    heading_deg=_dec(random.uniform(0, 360)),
                )

            self.stdout.write(f"    GPS trail: {len(expanded_trail)} points ({int(progress * 100)}% complete)")

            # 7. Create DriverLocation (current position = last GPS point)
            current_lat, current_lng = expanded_trail[-1]
            DriverLocation.objects.update_or_create(
                trip=trip,
                driver=driver,
                defaults={
                    "vehicle": vehicle,
                    "latitude": _dec(current_lat),
                    "longitude": _dec(current_lng),
                    "speed_kmh": _dec(random.uniform(40, 70)),
                    "heading_deg": _dec(random.uniform(0, 360)),
                },
            )
            self.stdout.write(f"    Driver location: ({current_lat:.4f}, {current_lng:.4f})")

        self.stdout.write(self.style.SUCCESS("\n✅ Tracking data seeded successfully!"))
        self.stdout.write(
            "\nTrips with live tracking data:\n"
            "  • Mumbai → Pune (65% complete)\n"
            "  • Delhi → Jaipur (40% complete)\n"
            "  • Bangalore → Chennai (80% complete)\n"
            "  • Hyderabad → Vijayawada (55% complete)\n"
        )

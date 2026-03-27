"""
Utility functions for the trips app.
"""

import math


def haversine_distance(lat1, lng1, lat2, lng2):
    """
    Calculate the great-circle distance between two points
    on Earth natively using the Haversine geometric formula without requiring PostGIS.
    Crucial for fast, in-memory proximity lookups.

    Returns deterministic direct distance scaled in meters.
    """
    R = 6_371_000  # Standard Earth's radius mapping in meters

    lat1_rad = math.radians(float(lat1))
    lat2_rad = math.radians(float(lat2))
    delta_lat = math.radians(float(lat2) - float(lat1))
    delta_lng = math.radians(float(lng2) - float(lng1))

    a = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lng / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return R * c


def is_inside_geofence(lat, lng, center_lat, center_lng, radius_meters):
    """
    Check if a dynamically moving entity point (lat, lng) breaks inside 
    a predefined static circular Geofence polygon.

    Args:
        lat, lng: Active ping coordinates
        center_lat, center_lng: The mapped origin anchor of the Geofence
        radius_meters: Permissible bounds expanding from the center

    Returns:
        True if the exact point mathematically sits on or within the defined radius curve.
    """
    distance = haversine_distance(lat, lng, center_lat, center_lng)
    return distance <= float(radius_meters)

# Geolocation & Live Tracking — Complete Reference

This guide covers every geolocation-related feature in the Fleet Management Server: static locations, geofences, GPS logging, driver live-location tracking, geofence events, route deviations, and real-time WebSocket updates.

**Base URL:** `http://localhost:8000/api/v1/`

**Authentication:** JWT Bearer Token
```
Header: Authorization: Bearer <access_token>
```

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Locations (Warehouses & Drop Points)](#2-locations-warehouses--drop-points)
3. [Geofences](#3-geofences)
4. [Geofence Events](#4-geofence-events)
5. [GPS Logs (History Trail)](#5-gps-logs-history-trail)
6. [Driver Locations (Live Tracking)](#6-driver-locations-live-tracking)
7. [Route Deviations](#7-route-deviations)
8. [Trip Tracking Shortcuts](#8-trip-tracking-shortcuts)
9. [WebSocket — Real-Time GPS Tracking](#9-websocket--real-time-gps-tracking)
10. [Database Tables & Schema](#10-database-tables--schema)
11. [End-to-End Flow](#11-end-to-end-flow)

---

## 1. Architecture Overview

The system provides two complementary ways to track a driver's position:

| Layer | Purpose | Table | Behaviour |
|---|---|---|---|
| **GPS Logs** | Full position history / breadcrumb trail | `gps_logs` | Appends a new row on every ping |
| **Driver Locations** | Current position snapshot | `driver_locations` | One row per trip + driver (upsert) |

Both layers can feed into the same **WebSocket room** (`trip_{id}_tracking`), so a fleet manager watching a trip receives updates in real time regardless of which method the driver uses.

```
Driver's Phone
    │
    ├──► POST /driver-locations/update_location/   (REST — upserts driver_locations)
    │         │
    │         ├──► DB: driver_locations (upsert)
    │         └──► WebSocket broadcast → trip_{id}_tracking
    │
    └──► ws/trips/{id}/gps/  (WebSocket — appends gps_logs)
              │
              ├──► DB: gps_logs (insert)
              └──► WebSocket broadcast → trip_{id}_tracking
                          │
                          ▼
                  Fleet Manager's Dashboard
                  (connected to same WS room)
```

---

## 2. Locations (Warehouses & Drop Points)

**Prefix:** `/api/v1/locations/`
**Permission:** Fleet Managers can create/update/delete. Others read-only.

These are static, named places (warehouses, drop-off points) used as trip origins and destinations.

### GET `/api/v1/locations/` — List Locations
**Filters:** `?is_warehouse=true`
**Search:** `?search=mumbai`

### GET `/api/v1/locations/{id}/` — Get Location Detail

### POST `/api/v1/locations/` — Create Location
**Auth:** fleet_manager only
```json
{
    "name": "Mumbai Warehouse",
    "address": "123, Industrial Area, Mumbai",    // optional
    "latitude": 19.0760000,                       // required, decimal (10,7)
    "longitude": 72.8777000,                      // required, decimal (10,7)
    "is_warehouse": true                          // optional (default: false)
}
```

### PUT `/api/v1/locations/{id}/` — Full Update
**Auth:** fleet_manager only
> Same fields as POST.

### PATCH `/api/v1/locations/{id}/` — Partial Update
**Auth:** fleet_manager only
```json
{
    "name": "Mumbai Warehouse Renamed"
}
```

### DELETE `/api/v1/locations/{id}/` — Delete Location
**Auth:** fleet_manager only

---

## 3. Geofences

**Prefix:** `/api/v1/geofences/`
**Permission:** Fleet Managers can create/update/delete. Others read-only.
**Note:** `created_by` is auto-set to the logged-in user.

Circular zones around key locations. When a vehicle enters or exits a geofence, a `GeofenceEvent` is recorded.

### GET `/api/v1/geofences/` — List Geofences
**Search:** `?search=warehouse`

### GET `/api/v1/geofences/{id}/` — Get Geofence Detail

### POST `/api/v1/geofences/` — Create Geofence
**Auth:** fleet_manager only
```json
{
    "name": "Mumbai Warehouse Zone",
    "location": 1,                      // optional, FK → Location ID
    "center_lat": 19.0760000,           // required, decimal (10,7)
    "center_lng": 72.8777000,           // required, decimal (10,7)
    "radius_meters": 500.00             // required, decimal (10,2)
}
```

### PUT `/api/v1/geofences/{id}/` — Full Update
**Auth:** fleet_manager only
```json
{
    "name": "Mumbai Warehouse Zone Updated",
    "location": 1,
    "center_lat": 19.0760000,
    "center_lng": 72.8777000,
    "radius_meters": 750.00
}
```

### PATCH `/api/v1/geofences/{id}/` — Partial Update
**Auth:** fleet_manager only
```json
{
    "radius_meters": 1000.00
}
```

### DELETE `/api/v1/geofences/{id}/` — Delete Geofence
**Auth:** fleet_manager only

---

## 4. Geofence Events

**Prefix:** `/api/v1/trips/geofence-events/`
**Permission:** Any authenticated user. **READ-ONLY.**

Automatically generated records when a vehicle enters or exits a geofence boundary.

### GET `/api/v1/trips/geofence-events/` — List Events
**Filters:** `?trip=1` `?vehicle=1` `?geofence=1` `?event_type=entry`

### GET `/api/v1/trips/geofence-events/{id}/` — Get Event Detail

**Response fields:**
```json
{
    "id": 1,
    "trip": 1,
    "vehicle": 2,
    "geofence": 1,
    "drop_point": 3,              // nullable — linked OrderDropPoint
    "event_type": "entry",        // "entry" | "exit"
    "latitude": "19.0760000",
    "longitude": "72.8777000",
    "occurred_at": "2026-03-22T14:30:00Z"
}
```

---

## 5. GPS Logs (History Trail)

**Prefix:** `/api/v1/trips/gps-logs/`
**Permission:** Any authenticated user.

A full breadcrumb trail of every GPS ping. Each call **creates a new row** — use this for historical playback and trail visualization.

### GET `/api/v1/trips/gps-logs/` — List GPS Logs
**Filters:** `?trip=1` `?vehicle=1`
**Ordering:** `?ordering=-recorded_at`

### GET `/api/v1/trips/gps-logs/{id}/` — Get GPS Log Detail

### POST `/api/v1/trips/gps-logs/` — Create GPS Log
```json
{
    "trip": 1,                         // required, FK → Trip ID
    "vehicle": 1,                      // required, FK → Vehicle ID
    "latitude": 19.0760000,           // required, decimal (10,7)
    "longitude": 72.8777000,          // required, decimal (10,7)
    "speed_kmh": 45.50,               // optional, decimal (6,2)
    "heading_deg": 180.00             // optional, decimal (5,2)
}
```

### PUT `/api/v1/trips/gps-logs/{id}/` — Full Update
> Same fields as POST.

### PATCH `/api/v1/trips/gps-logs/{id}/` — Partial Update
```json
{
    "speed_kmh": 50.00
}
```

### DELETE `/api/v1/trips/gps-logs/{id}/` — Delete GPS Log

---

## 6. Driver Locations (Live Tracking)

**Prefix:** `/api/v1/trips/driver-locations/`
**Permission:** Any authenticated user can read. Only **drivers** can update their location.

Unlike GPS Logs, this table maintains **one row per trip + driver**. The first call creates the entry; subsequent calls for the same trip + driver update it in place (upsert). This gives fleet managers an instant snapshot of every active driver's current position.

When a driver updates their location, the server also **broadcasts it to the WebSocket room** for that trip, so connected fleet managers see the change in real time.

### GET `/api/v1/trips/driver-locations/` — List Driver Locations
**Filters:** `?trip=1` `?driver=1` `?vehicle=1`

**Response (200):**
```json
{
    "count": 1,
    "next": null,
    "previous": null,
    "results": [
        {
            "id": 1,
            "trip": 1,
            "driver": 3,
            "vehicle": 2,
            "latitude": "19.0760000",
            "longitude": "72.8777000",
            "speed_kmh": "45.50",
            "heading_deg": "180.00",
            "updated_at": "2026-03-22T14:30:00Z"
        }
    ]
}
```

### GET `/api/v1/trips/driver-locations/{id}/` — Get Driver Location Detail

---

### POST `/api/v1/trips/driver-locations/update_location/` — Upsert Driver Location
**Auth:** Bearer Token (Driver only)

This is the primary endpoint called from the **driver's phone**. It creates a new location entry the first time a driver reports for a trip, and updates the existing entry on all subsequent calls for the same trip + driver.

**Request:**
```json
{
    "trip_id": 1,                      // required — must be in_progress and assigned to this driver
    "latitude": 19.0760000,           // required, decimal (10,7)
    "longitude": 72.8777000,          // required, decimal (10,7)
    "speed_kmh": 45.50,               // optional, decimal (6,2)
    "heading_deg": 180.00             // optional, decimal (5,2)
}
```

**Response (201 — first call / created):**
```json
{
    "id": 1,
    "trip": 1,
    "driver": 3,
    "vehicle": 2,
    "latitude": "19.0760000",
    "longitude": "72.8777000",
    "speed_kmh": "45.50",
    "heading_deg": "180.00",
    "updated_at": "2026-03-22T14:30:00Z"
}
```

**Response (200 — subsequent calls / updated):**
> Same shape as above, with updated coordinates and `updated_at`.

**Errors:**

| Status | Reason |
|---|---|
| 404 | Trip not found |
| 403 | Authenticated user is not the driver for this trip |
| 400 | Trip is not in `in_progress` status |

**Side effects:**
- Upserts a row in the `driver_locations` table (one row per trip + driver).
- Broadcasts the location update to the WebSocket channel group `trip_{trip_id}_tracking`, so any fleet manager connected to `ws/trips/{trip_id}/gps/` receives the update instantly.

---

## 7. Route Deviations

**Prefix:** `/api/v1/trips/route-deviations/`
**Permission:** Any authenticated user.

Records when a vehicle deviates from its planned route, with the deviation distance in meters.

### GET `/api/v1/trips/route-deviations/` — List Deviations
**Filters:** `?trip=1`

### GET `/api/v1/trips/route-deviations/{id}/` — Get Deviation Detail

### POST `/api/v1/trips/route-deviations/` — Create Deviation
```json
{
    "trip": 1,                         // required, FK → Trip ID
    "latitude": 19.1000000,           // required, decimal (10,7)
    "longitude": 72.9000000,          // required, decimal (10,7)
    "deviation_meters": 250.50,        // optional, decimal (10,2)
    "resolved_at": null                // optional, ISO datetime
}
```

### PATCH `/api/v1/trips/route-deviations/{id}/` — Partial Update
```json
{
    "resolved_at": "2026-03-22T15:00:00Z"
}
```

### DELETE `/api/v1/trips/route-deviations/{id}/` — Delete Deviation

---

## 8. Trip Tracking Shortcuts

These are convenience actions on the Trip endpoint that return location data without needing to query the GPS or driver-location tables directly.

**Prefix:** `/api/v1/trips/trips/{id}/`

### GET `/api/v1/trips/trips/{id}/tracking/` — Get Latest GPS Position
Returns the most recent `gps_logs` entry for the trip.

**Response (200):**
```json
{
    "id": 42,
    "trip": 1,
    "vehicle": 2,
    "latitude": "19.0760000",
    "longitude": "72.8777000",
    "speed_kmh": "45.50",
    "heading_deg": "180.00",
    "recorded_at": "2026-03-22T14:30:00Z"
}
```

**Response (404):** No GPS data available for this trip.

### GET `/api/v1/trips/trips/{id}/gps_history/` — Get Full GPS Trail
Returns the complete GPS breadcrumb trail for the trip, ordered by `recorded_at`. Paginated.

---

## 9. WebSocket — Real-Time GPS Tracking

**Protocol:** `ws://` (or `wss://` in production)
**Auth:** JWT token as query parameter

### Connection URL
```
ws://localhost:8000/ws/trips/{trip_id}/gps/?token=<access_token>
```

### How It Works

1. **Driver connects** — can send GPS data via WebSocket. Each message is saved to the `gps_logs` table and broadcast to all connected clients in the room.
2. **Fleet manager connects** — joins the same room and receives all GPS updates in real time.
3. **REST-to-WebSocket bridge** — when a driver calls `POST /driver-locations/update_location/`, the server also pushes the update into the WebSocket room. Fleet managers see it instantly even if the driver is not connected via WebSocket.

### Room Name
Each trip has a channel group named `trip_{trip_id}_tracking`. Anyone connected to the WebSocket URL for that trip is automatically added to this group.

### Send (Driver → Server)
```json
{
    "latitude": 19.0760000,
    "longitude": 72.8777000,
    "speed_kmh": 45.5,
    "heading_deg": 180.0
}
```

### Receive (Server → All Connected Clients)
```json
{
    "trip_id": 1,
    "driver_id": 3,
    "latitude": 19.0760000,
    "longitude": 72.8777000,
    "speed_kmh": 45.5,
    "heading_deg": 180.0,
    "updated_at": "2026-03-22T14:30:00Z"
}
```

### Error Response (via WebSocket)
```json
{
    "error": "latitude and longitude are required."
}
```

### Connection Lifecycle

| Event | What Happens |
|---|---|
| `connect` | User is authenticated via JWT in query string. Added to `trip_{id}_tracking` group. |
| `receive` | Driver sends GPS data → saved to `gps_logs` → broadcast to group. |
| `disconnect` | User is removed from the group. |

### Authentication Middleware
The server uses a custom `JWTAuthMiddleware` (`core/middleware.py`) that extracts the JWT from the `?token=` query parameter and attaches the authenticated user to `scope['user']`. Unauthenticated connections are rejected.

---

## 10. Database Tables & Schema

### `locations`
| Column | Type | Notes |
|---|---|---|
| `id` | BigAutoField | PK |
| `name` | CharField(200) | |
| `address` | TextField | nullable |
| `latitude` | Decimal(10,7) | |
| `longitude` | Decimal(10,7) | |
| `is_warehouse` | Boolean | default: false |
| `created_at` | DateTime | auto |

### `geofences`
| Column | Type | Notes |
|---|---|---|
| `id` | BigAutoField | PK |
| `location_id` | FK → locations | nullable |
| `name` | CharField(200) | |
| `center_lat` | Decimal(10,7) | |
| `center_lng` | Decimal(10,7) | |
| `radius_meters` | Decimal(10,2) | |
| `created_by_id` | FK → auth_user | nullable |
| `created_at` | DateTime | auto |
| `updated_at` | DateTime | auto |

### `geofence_events`
| Column | Type | Notes |
|---|---|---|
| `id` | BigAutoField | PK |
| `trip_id` | FK → trips | nullable |
| `vehicle_id` | FK → vehicles | |
| `geofence_id` | FK → geofences | |
| `drop_point_id` | FK → order_drop_points | nullable |
| `event_type` | CharField | `entry` / `exit` |
| `latitude` | Decimal(10,7) | nullable |
| `longitude` | Decimal(10,7) | nullable |
| `occurred_at` | DateTime | auto |

### `gps_logs`
| Column | Type | Notes |
|---|---|---|
| `id` | BigAutoField | PK |
| `trip_id` | FK → trips | indexed |
| `vehicle_id` | FK → vehicles | |
| `latitude` | Decimal(10,7) | |
| `longitude` | Decimal(10,7) | |
| `speed_kmh` | Decimal(6,2) | nullable |
| `heading_deg` | Decimal(5,2) | nullable |
| `recorded_at` | DateTime | auto, indexed (desc) |

### `driver_locations`
| Column | Type | Notes |
|---|---|---|
| `id` | BigAutoField | PK |
| `trip_id` | FK → trips | unique together with driver |
| `driver_id` | FK → auth_user | unique together with trip |
| `vehicle_id` | FK → vehicles | |
| `latitude` | Decimal(10,7) | |
| `longitude` | Decimal(10,7) | |
| `speed_kmh` | Decimal(6,2) | nullable |
| `heading_deg` | Decimal(5,2) | nullable |
| `updated_at` | DateTime | auto (updates on every save) |

**Constraint:** `UNIQUE (trip_id, driver_id)` — ensures one row per trip per driver.

### `route_deviations`
| Column | Type | Notes |
|---|---|---|
| `id` | BigAutoField | PK |
| `trip_id` | FK → trips | |
| `latitude` | Decimal(10,7) | |
| `longitude` | Decimal(10,7) | |
| `deviation_meters` | Decimal(10,2) | nullable |
| `detected_at` | DateTime | auto |
| `resolved_at` | DateTime | nullable |

---

## 11. End-to-End Flow

A complete location-tracking workflow from trip creation to live monitoring:

### Setup (Fleet Manager)
```
1. POST /api/v1/locations/          → Create warehouse + drop-point locations
2. POST /api/v1/geofences/          → Create geofences around key locations
3. POST /api/v1/trips/orders/       → Create order with drop points
4. POST /api/v1/trips/trips/        → Assign trip to driver + vehicle
```

### Trip Execution (Driver)
```
5. POST /api/v1/trips/trips/{id}/start/                      → Start the trip
6. POST /api/v1/trips/driver-locations/update_location/       → Send location (repeating)
       {trip_id, latitude, longitude, speed_kmh, heading_deg}
       ↳ Creates row on first call, updates on subsequent calls
       ↳ Broadcasts to WebSocket room automatically
```

### Live Monitoring (Fleet Manager)

**Option A — WebSocket (real-time):**
```
7a. Connect to  ws://localhost:8000/ws/trips/{trip_id}/gps/?token=<JWT>
    ↳ Receives location broadcasts instantly as driver moves
```

**Option B — REST (polling):**
```
7b. GET /api/v1/trips/driver-locations/?trip={trip_id}
    ↳ Returns current location snapshot
```

**Option C — GPS history:**
```
7c. GET /api/v1/trips/trips/{id}/gps_history/
    ↳ Returns full breadcrumb trail for map playback
```

### Trip Completion (Driver)
```
8. POST /api/v1/trips/trips/{id}/complete/   → End the trip
```

---

## Quick Reference: All Geolocation Endpoints

| Method | Endpoint | Purpose | Who |
|---|---|---|---|
| `GET` | `/api/v1/locations/` | List locations | Any |
| `POST` | `/api/v1/locations/` | Create location | Fleet Manager |
| `GET` | `/api/v1/geofences/` | List geofences | Any |
| `POST` | `/api/v1/geofences/` | Create geofence | Fleet Manager |
| `GET` | `/api/v1/trips/geofence-events/` | List geofence events | Any |
| `GET` | `/api/v1/trips/gps-logs/` | List GPS history | Any |
| `POST` | `/api/v1/trips/gps-logs/` | Log GPS point | Any |
| `GET` | `/api/v1/trips/driver-locations/` | List current locations | Any |
| `POST` | `/api/v1/trips/driver-locations/update_location/` | Upsert driver location | Driver |
| `GET` | `/api/v1/trips/route-deviations/` | List route deviations | Any |
| `POST` | `/api/v1/trips/route-deviations/` | Record deviation | Any |
| `GET` | `/api/v1/trips/trips/{id}/tracking/` | Latest GPS position | Any |
| `GET` | `/api/v1/trips/trips/{id}/gps_history/` | Full GPS trail | Any |
| `WS` | `ws/trips/{trip_id}/gps/` | Real-time GPS room | Any |

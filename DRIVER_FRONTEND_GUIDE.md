# Driver Frontend Guide

**Base URL:** `http://localhost:8000/api/v1/`  
**Auth Header:** `Authorization: Bearer <access_token>`  
**Content-Type:** `application/json`

---

## Table of Contents

1. [Driver Status Model](#1-driver-status-model)
2. [Clock-In / Clock-Out Flow](#2-clock-in--clock-out-flow)
3. [My Trips Screen](#3-my-trips-screen)
4. [Trip Detail Screen](#4-trip-detail-screen)
5. [Vehicle Info](#5-vehicle-info)
6. [Starting a Trip](#6-starting-a-trip)
7. [Completing a Trip](#7-completing-a-trip)
8. [Screen-by-Screen API Reference](#8-screen-by-screen-api-reference)
9. [Driver Status State Machine](#9-driver-status-state-machine)
10. [Important Rules for Frontend](#10-important-rules-for-frontend)

---

## 1. Driver Status Model

Every driver has a `driver_status` field on their profile. The fleet manager sees this status to know driver availability at any time.

| Status | Meaning | How it's set |
|---|---|---|
| `clocked_out` | Driver is not on duty. Not available for trips. | Default on registration. Set by `POST /auth/clock-out/` |
| `available` | Driver is on duty and ready to take a trip. | Set by `POST /auth/clock-in/` or after trip completes |
| `in_trip` | Driver is currently executing a trip. | Auto-set when driver starts a trip (`POST /trips/{id}/start/`) |

> **Key rule:** A driver can only be assigned a trip by the fleet manager when they are `clocked_out` or `available`. The frontend does **not** control assignment — the fleet manager does. The frontend only controls clock-in/out and trip start/complete.

---

## 2. Clock-In / Clock-Out Flow

### Clock-In

**Endpoint:** `POST /api/v1/auth/clock-in/`  
**Auth:** Bearer Token  
**Body:** *(empty — no body needed)*

**Success Response (200):**
```json
{
    "driver_status": "available",
    "detail": "Clocked in successfully. You are now available."
}
```

**Error Response (400) — if driver is currently on a trip:**
```json
{
    "detail": "Cannot clock in while on an active trip. Complete the trip first."
}
```

---

### Clock-Out

**Endpoint:** `POST /api/v1/auth/clock-out/`  
**Auth:** Bearer Token  
**Body:** *(empty — no body needed)*

**Success Response (200):**
```json
{
    "driver_status": "clocked_out",
    "detail": "Clocked out successfully. You are now unavailable."
}
```

**Error Response (400) — if driver is currently on a trip:**
```json
{
    "detail": "Cannot clock out while on an active trip. Complete the trip first."
}
```

---

### Frontend Logic for the Clock-In/Out Button

```
if driver_status == 'clocked_out'  → show "Clock In" button
if driver_status == 'available'    → show "Clock Out" button
if driver_status == 'in_trip'      → hide clock-in/out button (or show disabled state with tooltip "Complete your trip first")
```

After a successful clock-in/out call, refresh `GET /api/v1/auth/me/` to get the latest `profile.driver_status`.

---

## 3. My Trips Screen

The trips screen should show all trips assigned to the currently logged-in driver that are **active** (not yet completed or cancelled).

### Fetch Trips

**Endpoint:** `GET /api/v1/trips/trips/`  
**Auth:** Bearer Token  
**Recommended Filters:** `?driver=<current_user_id>&status=assigned` for pending trips, or `?driver=<current_user_id>&status=in_progress` for the active one.

To show all active trips in one call (use browser/app-level filter after fetching):
```
GET /api/v1/trips/trips/?driver=<current_user_id>
```

> Tip: Get `current_user_id` from `GET /api/v1/auth/me/` → `id` field.

---

### Trips List Table

Each row in the trips list should display:

| Column | Source in API Response | Notes |
|---|---|---|
| **Trip ID** | `id` | Use as reference |
| **Order Ref** | `order` → call `GET /trips/orders/{order}/` or get from trip detail | e.g. `ORD-2024-001` |
| **Source** | `source.name` + `source.address` | Departure warehouse |
| **Destinations** | Count from `destinations` array | e.g. "3 drop points" |
| **Scheduled Start** | `scheduled_start` | ISO datetime, format for display |
| **Vehicle** | Call `GET /fleet/vehicles/{vehicle}/` | Registration no. + model |
| **Assigned By** | Call `GET /users/{assigned_by}/` | Name of fleet manager who assigned |
| **Status** | `status` | `assigned` / `in_progress` / `completed` |

---

### Status Badge Colours (Suggested)

| Status | Colour |
|---|---|
| `assigned` | Blue |
| `in_progress` | Orange / Amber |
| `completed` | Green |
| `cancelled` | Red |
| `delayed` | Yellow |

---

## 4. Trip Detail Screen

When the driver taps a trip row, show full trip details.

### Fetch Trip Detail

**Endpoint:** `GET /api/v1/trips/trips/{id}/`  
**Auth:** Bearer Token

### Full Response Shape

```json
{
    "id": 1,
    "status": "assigned",
    "scheduled_start": "2024-06-15T08:00:00Z",

    "source": {
        "id": 1,
        "name": "Mumbai Warehouse",
        "address": "123 Industrial Area, Mumbai",
        "latitude": "19.0760000",
        "longitude": "72.8777000",
        "is_warehouse": true
    },

    "destinations": [
        {
            "id": 1,
            "sequence_no": 1,
            "location": {
                "id": 2,
                "name": "Pune Drop Point",
                "address": "456 MG Road, Pune",
                "latitude": "18.5204300",
                "longitude": "73.8567400",
                "is_warehouse": false
            },
            "contact_name": "Rajesh Kumar",
            "contact_phone": "+91-9876543210",
            "notes": "Ring bell twice",
            "status": "pending",
            "eta": null,
            "arrived_at": null,
            "delivered_at": null
        }
    ],

    "order": 1,
    "vehicle": 3,
    "driver": 2,
    "assigned_by": 5,

    "start_mileage_km": null,
    "end_mileage_km": null,
    "started_at": null,
    "ended_at": null,
    "created_at": "2024-06-14T10:00:00Z",
    "updated_at": "2024-06-14T10:00:00Z"
}
```

---

### Trip Detail Screen Sections

#### Section: Trip Info

| Label | Value |
|---|---|
| **Assigned By** | Resolved from `assigned_by` ID (see §5) |
| **Scheduled Start** | `scheduled_start` formatted as date + time |
| **Status** | `status` badge |

#### Section: Source (Pickup)

| Label | Value |
|---|---|
| **Warehouse Name** | `source.name` |
| **Address** | `source.address` |
| **Coordinates** | `source.latitude`, `source.longitude` — open in maps |

#### Section: Destinations (Drop Points)

Show each item in `destinations` array, **sorted by `sequence_no`**:

| Column | Value |
|---|---|
| **Stop #** | `sequence_no` |
| **Location** | `location.name` + `location.address` |
| **Contact** | `contact_name` + `contact_phone` |
| **Notes** | `notes` |
| **Status** | `status` badge (pending / arrived / delivered / failed) |

#### Section: Vehicle

| Label | Value |
|---|---|
| **Registration No.** | Fetched from `GET /fleet/vehicles/{vehicle}/` → `registration_no` |
| **Make & Model** | `make` + `model` |
| **Fuel Type** | `fuel_type` |

---

## 5. Vehicle Info

The trip detail response gives you a `vehicle` **ID** (integer). You need to make a separate call to get human-readable vehicle details.

**Endpoint:** `GET /api/v1/fleet/vehicles/{id}/`  
**Auth:** Bearer Token

**Key fields to display:**

| Field | Description |
|---|---|
| `registration_no` | Vehicle plate number, e.g. `MH12AB1234` |
| `make` | Manufacturer, e.g. `Tata` |
| `model` | Model name, e.g. `Ace Gold` |
| `fuel_type` | e.g. `diesel` |
| `capacity_kg` | Load capacity |
| `status` | `available` / `in_trip` / `under_maintenance` |

**Example call:**
```
GET /api/v1/fleet/vehicles/3/
Authorization: Bearer <token>
```

**Example response (key fields):**
```json
{
    "id": 3,
    "registration_no": "MH12AB1234",
    "make": "Tata",
    "model": "Ace Gold",
    "year": 2023,
    "fuel_type": "diesel",
    "capacity_kg": "750.00",
    "status": "available"
}
```

> **Frontend tip:** Cache vehicle data locally once fetched for a trip session. It won't change during the trip.

---

## 6. Starting a Trip

When the driver is ready to depart, they tap **"Start Trip"**.

> **Precondition:** Trip status must be `assigned`.  
> **Effect:** Trip status → `in_progress`, driver status → `in_trip`.

### UI: Show "Start Trip" button only when:
- `trip.status == 'assigned'`
- `driver.profile.driver_status == 'available'`

### API Call

**Endpoint:** `POST /api/v1/trips/trips/{id}/start/`  
**Auth:** Bearer Token  
**Body (all optional):**
```json
{
    "latitude": 19.0760000,
    "longitude": 72.8777000,
    "start_mileage_km": 15000.00
}
```

| Field | Description |
|---|---|
| `latitude` / `longitude` | Driver's current GPS location at trip start |
| `start_mileage_km` | Current odometer reading (if driver enters it) |

**Success Response (200):** Returns full updated trip object with `status: "in_progress"`.

**Error (400):** If trip is not in `assigned` status.

---

## 7. Completing a Trip

When all deliveries are done, driver taps **"Complete Trip"**.

> **Precondition:** Trip status must be `in_progress`.  
> **Effect:** Trip status → `completed`, driver status → `available`, vehicle status → `available`.

### UI: Show "Complete Trip" button only when:
- `trip.status == 'in_progress'`

### API Call

**Endpoint:** `POST /api/v1/trips/trips/{id}/complete/`  
**Auth:** Bearer Token  
**Body (all optional):**
```json
{
    "latitude": 18.5204300,
    "longitude": 73.8567400,
    "end_mileage_km": 15350.75
}
```

| Field | Description |
|---|---|
| `latitude` / `longitude` | Driver's current GPS location at end |
| `end_mileage_km` | Odometer reading at trip end |

**Success Response (200):** Returns full updated trip object with `status: "completed"`.

**Error (400):** If trip is not in `in_progress` status.

> After completing, the driver is automatically set to `available`. The frontend should then show the **Clock-Out** button again.

---

## 8. Screen-by-Screen API Reference

### Screen: Login

| Step | API Call |
|---|---|
| Login | `POST /api/v1/auth/token/` with `{username, password}` |
| Get profile | `GET /api/v1/auth/me/` |

### Screen: Home / Dashboard

| Step | API Call |
|---|---|
| Get current status | `GET /api/v1/auth/me/` → `profile.driver_status` |
| Clock in | `POST /api/v1/auth/clock-in/` |
| Clock out | `POST /api/v1/auth/clock-out/` |
| Get active trip | `GET /api/v1/trips/trips/?driver=<id>&status=in_progress` |

### Screen: My Trips List

| Step | API Call |
|---|---|
| Fetch all assigned trips | `GET /api/v1/trips/trips/?driver=<id>&status=assigned` |
| Fetch in-progress trip | `GET /api/v1/trips/trips/?driver=<id>&status=in_progress` |

### Screen: Trip Detail

| Step | API Call |
|---|---|
| Get trip data | `GET /api/v1/trips/trips/{id}/` |
| Get vehicle details | `GET /api/v1/fleet/vehicles/{vehicle_id}/` |
| Get assigned-by name | `GET /api/v1/users/{assigned_by_id}/` → `first_name` + `last_name` |
| Start trip | `POST /api/v1/trips/trips/{id}/start/` |
| Complete trip | `POST /api/v1/trips/trips/{id}/complete/` |

### Screen: GPS Tracking (Live)

| Step | API Call |
|---|---|
| Stream live GPS | WebSocket: `ws://host/ws/gps/{trip_id}/?token=<token>` |
| Get latest position | `GET /api/v1/trips/trips/{id}/tracking/` |

### Screen: Expenses

| Step | API Call |
|---|---|
| View trip expenses | `GET /api/v1/trips/trips/{id}/expenses/` |
| Add an expense | `POST /api/v1/trips/expenses/` |

---

## 9. Driver Status State Machine

```
     [ Registration ]
           │
           ▼
    ┌─────────────┐
    │ clocked_out │  ← Default. Driver is off duty.
    └──────┬──────┘
           │ POST /auth/clock-in/
           ▼
    ┌─────────────┐
    │  available  │  ← On duty. Fleet manager can assign trips.
    └──────┬──────┘
           │ POST /trips/{id}/start/  (driver starts a trip)
           ▼
    ┌─────────────┐
    │   in_trip   │  ← Actively on a trip. Cannot clock out.
    └──────┬──────┘
           │ POST /trips/{id}/complete/  (trip done)
           ▼
    ┌─────────────┐
    │  available  │  ← Back on duty. Can clock out or start next trip.
    └──────┬──────┘
           │ POST /auth/clock-out/
           ▼
    ┌─────────────┐
    │ clocked_out │
    └─────────────┘
```

> **Trip cancel** (fleet manager only from backend) also resets driver to `available`.

---

## 10. Important Rules for Frontend

| Rule | Detail |
|---|---|
| ❌ **No Cancel Trip button** | Drivers cannot cancel trips from the frontend. Only fleet managers can cancel. Do not expose this action in the driver UI. |
| ✅ **Clock-out blocked during trip** | The API will reject clock-out with 400 if `driver_status == in_trip`. Show a friendly message: *"Please complete your active trip before clocking out."* |
| ✅ **Destinations are ordered** | Always render `destinations` sorted by `sequence_no` (API returns them pre-sorted, but defensive sort on frontend is good practice). |
| ✅ **Fetch vehicle info separately** | Trip detail only gives `vehicle: <id>`. Make a second call to `GET /api/v1/fleet/vehicles/{id}/` to display registration number, make, and model. |
| ✅ **Assigned By is a user ID** | Trip detail gives `assigned_by: <id>`. Make a call to `GET /api/v1/users/{id}/` to display the fleet manager's name. |
| ✅ **Refresh Me after clock actions** | After any clock-in/out call, refresh `GET /api/v1/auth/me/` to sync local state with server. |
| ✅ **Handle `scheduled_start: null`** | A trip may not have a scheduled start. Show "Not set" in that case. |
| ✅ **GPS permission** | Ask for location permission before starting a trip so coordinates can be sent to `/start/` and `/complete/`. |
| ⚠️ **Token expiry** | Access tokens expire. Use `POST /api/v1/auth/token/refresh/` with the refresh token to get a new access token silently before retrying failed requests. |

---

## Supplementary: Me Response — Profile Fields

`GET /api/v1/auth/me/` returns:

```json
{
    "id": 2,
    "username": "john_driver",
    "email": "john@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "profile": {
        "role": "driver",
        "phone": "+91-9876543210",
        "profile_photo": null,
        "is_active": true,
        "first_time_login": false,
        "driver_status": "available",
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-06-15T08:00:00Z"
    }
}
```

Use `profile.driver_status` to control all clock-in/out UI.  
Use `profile.first_time_login` to redirect the driver to a change-password screen on first login.

# Fleet Management API – Complete Reference

**Base URL:** `http://localhost:8000/api/v1/`

**Authentication:** JWT Bearer Token (except registration & login)
```
Header: Authorization: Bearer <access_token>
```

**Content-Type:** `application/json` (unless uploading files → `multipart/form-data`)

**User Roles:** `driver`, `fleet_manager`, `maintenance_staff`

---

## Table of Contents

1. [Authentication](#1-authentication)
2. [Users](#2-users)
3. [Locations](#3-locations)
4. [Geofences](#4-geofences)
5. [Vehicles](#5-vehicles)
6. [Inspection Checklists](#6-inspection-checklists)
7. [Inspection Checklist Items](#7-inspection-checklist-items)
8. [Inspections](#8-inspections)
9. [Vehicle Issues](#9-vehicle-issues)
10. [Orders](#10-orders)
11. [Order Drop Points](#11-order-drop-points)
12. [Trips](#12-trips)
13. [Routes](#13-routes)
14. [Route Deviations](#14-route-deviations)
15. [GPS Logs](#15-gps-logs)
16. [Driver Locations (Live Tracking)](#16-driver-locations-live-tracking)
17. [Geofence Events](#17-geofence-events)
18. [Trip Expenses](#18-trip-expenses)
19. [Fuel Logs](#19-fuel-logs)
20. [Delivery Proofs](#20-delivery-proofs)
21. [Maintenance Schedules](#21-maintenance-schedules)
22. [Maintenance Records](#22-maintenance-records)
23. [Spare Parts](#23-spare-parts)
24. [Messages](#24-messages)
25. [Notifications](#25-notifications)
26. [SOS Alerts](#26-sos-alerts)
27. [WebSocket Endpoints](#27-websocket-endpoints)
28. [Driver Availability — Clock-In & Clock-Out](#28-driver-availability--clock-in--clock-out)
29. [Driver Documents](#29-driver-documents)
30. [Profile Images](#30-profile-images)
31. [Odometer Images](#31-odometer-images)
32. [Leave Requests](#32-leave-requests)
33. [Spare Parts Used (Legacy)](#33-spare-parts-used-legacy)

---

## 1. Authentication

### POST `/api/v1/auth/register/` — Register New User
**Auth:** None
```json
{
    "username": "john_driver",
    "email": "john@example.com",
    "password": "securepass123",
    "first_name": "John",          // optional
    "last_name": "Doe",            // optional
    "role": "driver",              // required: "driver" | "fleet_manager" | "maintenance_staff"
    "phone": "+91-9876543210"      // optional
}
```
**Response:** Returns user object + `tokens.access` and `tokens.refresh`

---

### POST `/api/v1/auth/token/` — Login (Get Token Pair)
**Auth:** None
```json
{
    "username": "john_driver",
    "password": "securepass123"
}
```
**Response:**
```json
{
    "access": "<access_token>",
    "refresh": "<refresh_token>"
}
```

---

### POST `/api/v1/auth/token/refresh/` — Refresh Access Token
**Auth:** None
```json
{
    "refresh": "<refresh_token>"
}
```

---

### GET `/api/v1/auth/me/` — Get Current User Profile
**Auth:** Bearer Token

---

### PUT/PATCH `/api/v1/auth/me/` — Update Profile
**Auth:** Bearer Token
```json
{
    "first_name": "John",          // optional
    "last_name": "Doe",            // optional
    "email": "newemail@example.com", // optional
    "phone": "+91-9876543210",     // optional
    "first_time_login": false      // optional, boolean
}
```
> For `profile_photo` upload, use `multipart/form-data`

**`GET /api/v1/auth/me/` response shape includes:**
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
        "driver_status": "available",   // "available" | "in_trip" | "clocked_out" | "on_rest" | "on_leave"
        "rest_ends_at": null,           // ISO datetime — set when driver_status = "on_rest"; null otherwise
        "driving_licence": null,        // absolute URL of uploaded driving licence file, or null
        "aadhaar_card": null,           // absolute URL of uploaded aadhaar card file, or null
        "created_at": "...",
        "updated_at": "..."
    }
}

---

### POST `/api/v1/auth/change-password/` — Change Password
**Auth:** Bearer Token
```json
{
    "old_password": "currentpass123",
    "new_password": "newsecurepass456"
}
```
> **Note:** Successfully changing the password will automatically set the user's `first_time_login` flag to `false`.

---

### POST `/api/v1/auth/send-credentials/` — Send Credentials via Email
**Auth:** Bearer Token
```json
{
    "email": "user@example.com",       // required, recipient email address
    "userid": "john_driver",           // required, username to send
    "password": "securepass123"        // required, password to send
}
```
**Response (200):**
```json
{
    "detail": "Credentials sent successfully to user@example.com."
}
```
**Error (400):** Missing fields → returns field-level errors.
**Error (500):** Email delivery failure → `{"detail": "Failed to send email: ..."}`

---

## 2. Users

### GET `/api/v1/users/` — List Users
**Auth:** Bearer Token
**Filters:** `?profile__role=driver` `?is_active=true`
**Search:** `?search=john`

### GET `/api/v1/users/{id}/` — Get User Detail
**Auth:** Bearer Token

> Users endpoint is **read-only**.

---

## 3. Locations

**Permission:** Fleet Managers can create/update/delete. Others read-only.

### GET `/api/v1/locations/` — List Locations
**Auth:** Bearer Token
**Filters:** `?is_warehouse=true`
**Search:** `?search=mumbai`

### GET `/api/v1/locations/{id}/` — Get Location Detail
**Auth:** Bearer Token

### POST `/api/v1/locations/` — Create Location
**Auth:** Bearer Token (fleet_manager only)
```json
{
    "name": "Mumbai Warehouse",
    "address": "123, Industrial Area, Mumbai",    // optional (default: "")
    "latitude": 19.0760000,                       // required, decimal (10,7)
    "longitude": 72.8777000,                      // required, decimal (10,7)
    "is_warehouse": true                          // optional (default: false)
}
```

### PUT `/api/v1/locations/{id}/` — Full Update Location
**Auth:** Bearer Token (fleet_manager only)
```json
{
    "name": "Mumbai Warehouse Updated",
    "address": "456, Industrial Area, Mumbai",
    "latitude": 19.0760000,
    "longitude": 72.8777000,
    "is_warehouse": true
}
```

### PATCH `/api/v1/locations/{id}/` — Partial Update Location
**Auth:** Bearer Token (fleet_manager only)
```json
{
    "name": "Mumbai Warehouse Renamed"
}
```

### DELETE `/api/v1/locations/{id}/` — Delete Location
**Auth:** Bearer Token (fleet_manager only)

---

## 4. Geofences

**Permission:** Fleet Managers can create/update/delete. Others read-only.
**Note:** `created_by` is auto-set to the logged-in user.

### GET `/api/v1/geofences/` — List Geofences
**Auth:** Bearer Token
**Search:** `?search=warehouse`

### GET `/api/v1/geofences/{id}/` — Get Geofence Detail
**Auth:** Bearer Token

### POST `/api/v1/geofences/` — Create Geofence
**Auth:** Bearer Token (fleet_manager only)
```json
{
    "name": "Mumbai Warehouse Zone",
    "location": 1,                      // optional, FK → Location ID
    "center_lat": 19.0760000,           // required, decimal (10,7)
    "center_lng": 72.8777000,           // required, decimal (10,7)
    "radius_meters": 500.00             // required, decimal (10,2)
}
```

### PUT `/api/v1/geofences/{id}/` — Full Update Geofence
**Auth:** Bearer Token (fleet_manager only)
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
**Auth:** Bearer Token (fleet_manager only)
```json
{
    "radius_meters": 1000.00
}
```

### DELETE `/api/v1/geofences/{id}/` — Delete Geofence
**Auth:** Bearer Token (fleet_manager only)

---

## 5. Vehicles

**Permission:** Fleet Managers can create/update/delete. Others read-only.

### GET `/api/v1/fleet/vehicles/` — List Vehicles
**Auth:** Bearer Token
**Filters:** `?status=available` `?fuel_type=diesel` `?make=Tata`
**Search:** `?search=MH12`
**Ordering:** `?ordering=-current_mileage_km`

### GET `/api/v1/fleet/vehicles/{id}/` — Get Vehicle Detail
**Auth:** Bearer Token

### POST `/api/v1/fleet/vehicles/` — Create Vehicle
**Auth:** Bearer Token (fleet_manager only)
```json
{
    "registration_no": "MH12AB1234",               // required, unique, max 50
    "make": "Tata",                                 // required, max 100
    "model": "Ace Gold",                            // required, max 100
    "year": 2023,                                   // optional
    "vin": "MALA851CLHM123456",                     // optional, unique, max 100
    "fuel_type": "diesel",                          // optional (default: "")
    "capacity_kg": 750.00,                          // optional, decimal (10,2) — payload weight capacity
    "capacity_litre": 5000.00,                      // optional, decimal (10,2) — tank/cargo volume capacity
    "status": "available",                          // optional: "available"|"in_trip"|"idle"|"under_maintenance"
    "current_mileage_km": 15000.00,                 // optional (default: 0)
    "last_service_date": "2024-01-15",              // optional, date YYYY-MM-DD
    "next_service_due_km": 20000.00,                // optional
    "next_service_due_date": "2025-01-15"           // optional, date YYYY-MM-DD
}
```

### PUT `/api/v1/fleet/vehicles/{id}/` — Full Update Vehicle
**Auth:** Bearer Token (fleet_manager only)
> Send all writable fields (same as POST).

### PATCH `/api/v1/fleet/vehicles/{id}/` — Partial Update Vehicle
**Auth:** Bearer Token (fleet_manager only)
```json
{
    "status": "under_maintenance",
    "current_mileage_km": 16500.50
}
```

### DELETE `/api/v1/fleet/vehicles/{id}/` — Delete Vehicle
**Auth:** Bearer Token (fleet_manager only)

### GET `/api/v1/fleet/vehicles/{id}/inspections/` — List Vehicle's Inspections
**Auth:** Bearer Token

### GET `/api/v1/fleet/vehicles/{id}/issues/` — List Vehicle's Issues
**Auth:** Bearer Token

---

## 6. Inspection Checklists

**Permission:** Maintenance Staff or Fleet Manager only.

### GET `/api/v1/fleet/checklists/` — List Checklists
**Auth:** Bearer Token
**Filters:** `?is_active=true`

### GET `/api/v1/fleet/checklists/{id}/` — Get Checklist Detail (includes items)
**Auth:** Bearer Token

### POST `/api/v1/fleet/checklists/` — Create Checklist
**Auth:** Bearer Token (maintenance_staff or fleet_manager)
```json
{
    "name": "Pre-Trip Safety Check",       // required, max 150
    "is_active": true                      // optional (default: true)
}
```

### PUT `/api/v1/fleet/checklists/{id}/` — Full Update Checklist
**Auth:** Bearer Token (maintenance_staff or fleet_manager)
```json
{
    "name": "Pre-Trip Safety Check v2",
    "is_active": true
}
```

### PATCH `/api/v1/fleet/checklists/{id}/` — Partial Update
**Auth:** Bearer Token (maintenance_staff or fleet_manager)
```json
{
    "is_active": false
}
```

### DELETE `/api/v1/fleet/checklists/{id}/` — Delete Checklist
**Auth:** Bearer Token (maintenance_staff or fleet_manager)

---

## 7. Inspection Checklist Items

**Permission:** Maintenance Staff or Fleet Manager only.

### GET `/api/v1/fleet/checklist-items/` — List Items
**Auth:** Bearer Token
**Filters:** `?checklist=1`

### GET `/api/v1/fleet/checklist-items/{id}/` — Get Item Detail
**Auth:** Bearer Token

### POST `/api/v1/fleet/checklist-items/` — Create Item
**Auth:** Bearer Token (maintenance_staff or fleet_manager)
```json
{
    "checklist": 1,                        // required, FK → InspectionChecklist ID
    "item_name": "Check tire pressure",    // required, max 200
    "sequence_no": 1,                      // required, integer
    "is_required": true                    // optional (default: true)
}
```

### PUT `/api/v1/fleet/checklist-items/{id}/` — Full Update
**Auth:** Bearer Token (maintenance_staff or fleet_manager)
```json
{
    "checklist": 1,
    "item_name": "Check tire pressure (all 4)",
    "sequence_no": 1,
    "is_required": true
}
```

### PATCH `/api/v1/fleet/checklist-items/{id}/` — Partial Update
**Auth:** Bearer Token (maintenance_staff or fleet_manager)
```json
{
    "item_name": "Check tire pressure (all 6)"
}
```

### DELETE `/api/v1/fleet/checklist-items/{id}/` — Delete Item
**Auth:** Bearer Token (maintenance_staff or fleet_manager)

---

## 8. Inspections

**Permission:** Any authenticated user.

### GET `/api/v1/fleet/inspections/` — List Inspections
**Auth:** Bearer Token
**Filters:** `?vehicle=1` `?driver=1` `?inspection_type=pre_trip` `?overall_status=pending`
**Ordering:** `?ordering=-submitted_at`

### GET `/api/v1/fleet/inspections/{id}/` — Get Inspection Detail (includes results)
**Auth:** Bearer Token

### POST `/api/v1/fleet/inspections/` — Create Inspection (with nested results)
**Auth:** Bearer Token
**Note:** `driver` is auto-set to the logged-in user.
```json
{
    "trip": 1,                                     // optional, FK → Trip ID
    "vehicle": 1,                                  // required, FK → Vehicle ID
    "checklist": 1,                                // optional, FK → InspectionChecklist ID
    "inspection_type": "pre_trip",                 // optional: "pre_trip"|"post_trip"|"ad_hoc" (default: "pre_trip")
    "notes": "Overall condition looks good",       // optional
    "results": [                                   // required, array
        {
            "checklist_item_id": 1,                // required, FK → InspectionChecklistItem ID
            "result": "pass",                      // required: "pass"|"fail"|"na"
            "notes": "",                           // optional
            "photo_url": ""                        // optional, valid URL
        },
        {
            "checklist_item_id": 2,
            "result": "fail",
            "notes": "Left front tire pressure low",
            "photo_url": "https://example.com/photo1.jpg"
        }
    ]
}
```

### PUT `/api/v1/fleet/inspections/{id}/` — Full Update Inspection
**Auth:** Bearer Token
> Same format as POST.

### PATCH `/api/v1/fleet/inspections/{id}/` — Partial Update
**Auth:** Bearer Token
```json
{
    "notes": "Updated notes after review"
}
```

### POST `/api/v1/fleet/inspections/{id}/review/` — Review Inspection
**Auth:** Bearer Token (maintenance_staff or fleet_manager)
```json
{
    "overall_status": "approved"           // required: "approved"|"flagged"
}
```

### POST `/api/v1/fleet/inspections/{id}/approve/` — Approve a Flagged Inspection
**Auth:** Bearer Token (fleet_manager only)
**Note:** Sets `approved = true` on the inspection. No request body required.
**Response:** Full inspection object with `"approved": true`.

### DELETE `/api/v1/fleet/inspections/{id}/` — Delete Inspection
**Auth:** Bearer Token

> **New field:** All inspection responses now include `"approved": false|true` — defaults to `false` on creation, set to `true` via the `/approve/` action above.

---

## 9. Vehicle Issues

**Permission:** Any authenticated user.
**Note:** `reported_by` is auto-set to the logged-in user.

### GET `/api/v1/fleet/issues/` — List Issues
**Auth:** Bearer Token
**Filters:** `?vehicle=1` `?reported_by=1` `?severity=high` `?status=reported`
**Search:** `?search=brake`
**Ordering:** `?ordering=-reported_at`

### GET `/api/v1/fleet/issues/{id}/` — Get Issue Detail
**Auth:** Bearer Token

### POST `/api/v1/fleet/issues/` — Report Issue
**Auth:** Bearer Token
```json
{
    "vehicle": 1,                      // required, FK → Vehicle ID
    "inspection": 1,                   // optional, FK → Inspection ID
    "title": "Brake pads worn",        // required, max 255
    "description": "Front brake pads showing significant wear", // optional
    "severity": "high",                // optional: "low"|"medium"|"high"|"critical" (default: "medium")
    "status": "reported",              // optional: "reported"|"acknowledged"|"in_repair"|"resolved" (default: "reported")
    "photo_url": "https://example.com/brake.jpg" // optional, valid URL
}
```

### PUT `/api/v1/fleet/issues/{id}/` — Full Update Issue
**Auth:** Bearer Token
```json
{
    "vehicle": 1,
    "inspection": null,
    "title": "Brake pads worn out completely",
    "description": "Front brake pads need immediate replacement",
    "severity": "critical",
    "status": "acknowledged",
    "photo_url": "https://example.com/brake2.jpg"
}
```

### PATCH `/api/v1/fleet/issues/{id}/` — Partial Update Issue
**Auth:** Bearer Token
```json
{
    "status": "in_repair",
    "severity": "critical"
}
```

### POST `/api/v1/fleet/vehicle-issues/{id}/approve/` — Approve a Vehicle Issue
**Auth:** Bearer Token (fleet_manager only)
**Note:** Sets `approved = true` on the issue. No request body required.
**Response:** Full issue object with `"approved": true`.

### DELETE `/api/v1/fleet/issues/{id}/` — Delete Issue
**Auth:** Bearer Token

> **New field:** All vehicle issue responses now include `"approved": false|true` — defaults to `false` on creation, set to `true` via the `/approve/` action above.

#### 🔁 Automatic Vehicle Status Sync (DB Trigger)

A PostgreSQL trigger (`trg_vehicle_status_from_issue`) fires automatically on every **INSERT**, **UPDATE of status**, and **DELETE** on the `vehicle_issues` table and keeps `vehicles.status` in sync without any extra API call.

| Vehicle Issue `status` | Effect on `vehicles.status` |
|---|---|
| `reported` | → `under_maintenance` |
| `acknowledged` | → `under_maintenance` |
| `in_repair` | → `under_maintenance` |
| `resolved` | → `available` *(only when no other open issues remain for that vehicle)* |
| Issue **deleted** | Recalculates — `available` if no open issues remain, otherwise stays `under_maintenance` |

**Multi-issue safety:** The trigger scans **all** open issues for the vehicle before updating its status. Resolving one issue out of two will **not** flip the vehicle to `available` while the other issue is still open.

**Override note:** The trigger fires unconditionally — it will override `in_trip` status too. The fleet manager will see the conflict immediately and can handle it.

---

## 10. Orders

**Permission:** Fleet Managers can create/update/delete. Others read-only.
**Note:** `created_by` is auto-set to the logged-in user.

### GET `/api/v1/trips/orders/` — List Orders
**Auth:** Bearer Token
**Filters:** `?status=pending` `?warehouse=1` `?created_by=1`
**Search:** `?search=ORD-001`
**Ordering:** `?ordering=-created_at`

### GET `/api/v1/trips/orders/{id}/` — Get Order Detail (includes drop_points)
**Auth:** Bearer Token

### POST `/api/v1/trips/orders/` — Create Order (with nested drop points)
**Auth:** Bearer Token (fleet_manager only)
```json
{
    "order_ref": "ORD-2024-001",                   // required, unique, max 50
    "warehouse": 1,                                // required, FK → Location ID (is_warehouse=true)
    "notes": "Handle with care",                   // optional
    "capacity_litre": 2000.00,                     // optional, decimal (10,2) — cargo volume
    "capacity_kg": 500.00,                         // optional, decimal (10,2) — cargo weight
    "drop_points": [                               // required, array
        {
            "location_id": 2,                      // required, FK → Location ID
            "sequence_no": 1,                      // required, integer
            "contact_name": "Rajesh Kumar",        // optional
            "contact_phone": "+91-9876543210",     // optional
            "notes": "Ring bell twice"             // optional
        },
        {
            "location_id": 3,
            "sequence_no": 2,
            "contact_name": "Priya Sharma",
            "contact_phone": "+91-9876543211",
            "notes": ""
        }
    ]
}
```

### PUT `/api/v1/trips/orders/{id}/` — Full Update Order
**Auth:** Bearer Token (fleet_manager only)
```json
{
    "order_ref": "ORD-2024-001",
    "warehouse": 1,
    "status": "assigned",                          // "pending"|"assigned"|"in_transit"|"delivered"|"failed"
    "notes": "Updated notes"
}
```

### PATCH `/api/v1/trips/orders/{id}/` — Partial Update Order
**Auth:** Bearer Token (fleet_manager only)
```json
{
    "status": "assigned"
}
```

### DELETE `/api/v1/trips/orders/{id}/` — Delete Order
**Auth:** Bearer Token (fleet_manager only)

### PATCH `/api/v1/trips/orders/{id}/drop_points/` — Replace All Drop Points
**Auth:** Bearer Token (fleet_manager only)  
**Note:** Deletes all existing drop points for the order and replaces them with the provided list. Sequence numbers must be unique within the list.
```json
{
    "drop_points": [
        {
            "location_id": 2,                      // required, FK → Location ID
            "sequence_no": 1,                      // required, integer (must be unique)
            "contact_name": "Rajesh Kumar",        // optional
            "contact_phone": "+91-9876543210",     // optional
            "notes": "Ring bell twice"             // optional
        },
        {
            "location_id": 5,
            "sequence_no": 2,
            "contact_name": "Priya Sharma",
            "contact_phone": "+91-9876543211",
            "notes": ""
        }
    ]
}
```
**Response:** Full order object with updated `drop_points` array.

---

## 11. Order Drop Points

**Permission:** Any authenticated user.

### GET `/api/v1/trips/drop-points/` — List Drop Points
**Auth:** Bearer Token
**Filters:** `?order=1` `?status=pending`

### GET `/api/v1/trips/drop-points/{id}/` — Get Drop Point Detail
**Auth:** Bearer Token

### POST `/api/v1/trips/drop-points/` — Create Drop Point
**Auth:** Bearer Token
```json
{
    "order": 1,                        // required (but read_only in serializer — set via URL/nested)
    "location": 2,                     // required, FK → Location ID
    "sequence_no": 3,                  // required, integer
    "contact_name": "Name",           // optional
    "contact_phone": "+91-9876543210", // optional
    "notes": "",                       // optional
    "status": "pending",              // optional: "pending"|"in_transit"|"arrived"|"delivered"|"failed"
    "eta": "2024-06-15T10:30:00Z"     // optional, ISO datetime
}
```

### PATCH `/api/v1/trips/drop-points/{id}/` — Mark Drop Point Status (Partial Completion)
**Auth:** Bearer Token
**Note:** Drivers use this to mark each stop as they complete it. `arrived_at` and `delivered_at` timestamps are auto-set on status transitions.
```json
{
    "status": "arrived"      // "pending"|"in_transit"|"arrived"|"delivered"|"failed"
}
```
**Multi-destination workflow:**
1. Driver arrives at Drop #1 → `PATCH` with `{"status": "arrived"}` → `arrived_at` auto-set
2. Driver delivers at Drop #1 → `PATCH` with `{"status": "delivered"}` → `delivered_at` auto-set
3. Repeat for Drop #2, #3, ...
4. After last drop → `POST /api/v1/trips/trips/{id}/complete/` to finish the trip

### DELETE `/api/v1/trips/drop-points/{id}/` — Delete Drop Point
**Auth:** Bearer Token

---

## 12. Trips

**Permission:** Any authenticated user.
**Note:** `assigned_by` is auto-set to the logged-in user on creation.

**Trip Status Values:**

| Value | Meaning |
|---|---|
| `pending` | Created but no driver assigned yet, OR driver rejected the assigned trip |
| `assigned` | Assigned to a driver, awaiting acceptance |
| `in_progress` | Driver accepted and started the trip |
| `completed` | Trip finished |
| `cancelled` | Trip cancelled |
| `delayed` | Trip is delayed |

### GET `/api/v1/trips/trips/` — List Trips
**Auth:** Bearer Token
**Filters:** `?status=assigned` `?status=pending` `?driver=1` `?vehicle=1` `?order=1`
**Search:** `?search=ORD-001`
**Ordering:** `?ordering=-created_at` `?ordering=scheduled_start`

### GET `/api/v1/trips/trips/{id}/` — Get Trip Detail
**Auth:** Bearer Token

Returns trip data including `source` (departure warehouse) and `destinations` (all ordered drop points), giving the driver a full trip briefing in a single call.

**Response includes:**
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
    "route_detail": { ... },
    "order": 1,
    "vehicle": 1,
    "driver": 2,
    "assigned_by": 3,
    "start_mileage_km": null,
    "end_mileage_km": null,
    "started_at": null,
    "ended_at": null,
    "created_at": "...",
    "updated_at": "..."
}
```

> `source` — the warehouse the trip departs from (from the linked order).
> `destinations` — all drop points in delivery sequence order. Each contains the full location (address + coordinates) and contact details.

### POST `/api/v1/trips/trips/` — Create Trip
**Auth:** Bearer Token
```json
{
    "order": 1,                        // required, FK → Order ID
    "vehicle": 1,                      // required, FK → Vehicle ID
    "driver": 2,                       // required, FK → User ID (driver)
    "scheduled_start": "2024-06-15T08:00:00Z",  // optional, ISO datetime
    "start_mileage_km": 15000.00       // optional, decimal
}
```

### PUT `/api/v1/trips/trips/{id}/` — Full Update Trip
**Auth:** Bearer Token
```json
{
    "order": 1,
    "vehicle": 1,
    "driver": 2,
    "status": "assigned",             // "pending"|"assigned"|"in_progress"|"completed"|"cancelled"|"delayed"
    "scheduled_start": "2024-06-15T09:00:00Z",
    "start_mileage_km": 15000.00,
    "end_mileage_km": null,
    "start_location_lat": null,
    "start_location_lng": null,
    "end_location_lat": null,
    "end_location_lng": null
}
```

### PATCH `/api/v1/trips/trips/{id}/` — Partial Update Trip
**Auth:** Bearer Token
```json
{
    "status": "delayed",
    "scheduled_start": "2024-06-15T10:00:00Z"
}
```

### DELETE `/api/v1/trips/trips/{id}/` — Delete Trip
**Auth:** Bearer Token

---

### POST `/api/v1/trips/trips/{id}/start/` — Start Trip
**Auth:** Bearer Token
**Precondition:** Trip status must be `assigned`
```json
{
    "latitude": 19.0760000,            // optional
    "longitude": 72.8777000,           // optional
    "start_mileage_km": 15000.00       // optional (overrides existing)
}
```

### POST `/api/v1/trips/trips/{id}/complete/` — Complete Trip
**Auth:** Bearer Token
**Precondition:** Trip status must be `in_progress`
```json
{
    "latitude": 18.5204300,            // optional
    "longitude": 73.8567400,           // optional
    "end_mileage_km": 15350.75         // optional
}
```

### POST `/api/v1/trips/trips/{id}/cancel/` — Cancel Trip
**Auth:** Bearer Token
**Precondition:** Trip status must NOT be `completed` or `cancelled`
```json
{}
```
> No body required.

---

### POST `/api/v1/trips/trips/{id}/accept/` — Accept Trip (Driver)
**Auth:** Bearer Token (assigned driver only)
**Precondition:** Trip status must be `assigned`
```json
{
    "latitude": 19.0760000,            // optional
    "longitude": 72.8777000,           // optional
    "start_mileage_km": 15000.00       // optional
}
```
**Response (200):** Full trip object with `"status": "in_progress"`.

> **Side effects:** Sets `status=in_progress`, `started_at=now`, vehicle `status=in_trip`, order `status=in_transit`, driver `driver_status=in_trip`. Behaves identically to `/start/` but is named semantically for the driver-acceptance workflow.

---

### POST `/api/v1/trips/trips/{id}/reject/` — Reject Trip (Driver)
**Auth:** Bearer Token (assigned driver only)
**Precondition:** Trip status must be `assigned`
```json
{
    "reason": "Vehicle has a flat tyre, cannot proceed"   // optional, rejection reason
}
```
**Response (200):** Full trip object with `"status": "pending"`.

> **Side effects:** Sets `status=pending`, clears `driver` assignment, sets vehicle `status=available`, stores `rejection_reason`. Sends a notification to **all fleet managers** with the driver's rejection reason so they can reassign.

**Notification sent to all fleet managers:**
```json
{
    "alert_type": "trip_rejected",
    "title": "Trip #<id> rejected by <driver_name>",
    "body": "<reason>",
    "reference_id": <trip_id>,
    "reference_type": "trip"
}
```

---

### GET `/api/v1/trips/trips/{id}/tracking/` — Get Latest GPS Position
**Auth:** Bearer Token

### GET `/api/v1/trips/trips/{id}/gps_history/` — Get Full GPS Trail
**Auth:** Bearer Token

### GET `/api/v1/trips/trips/{id}/expenses/` — Get Trip Expenses
**Auth:** Bearer Token

### GET `/api/v1/trips/trips/{id}/fuel/` — Get Trip Fuel Logs
**Auth:** Bearer Token

---

## 13. Routes

**Permission:** Any authenticated user.

### GET `/api/v1/trips/routes/` — List Routes
**Auth:** Bearer Token
**Filters:** `?trip=1`

### GET `/api/v1/trips/routes/{id}/` — Get Route Detail
**Auth:** Bearer Token

### POST `/api/v1/trips/routes/` — Create Route
**Auth:** Bearer Token
```json
{
    "trip": 1,                                     // required, FK → Trip ID (OneToOne)
    "origin_lat": 19.0760000,                      // required, decimal (10,7)
    "origin_lng": 72.8777000,                      // required, decimal (10,7)
    "destination_lat": 18.5204300,                 // required, decimal (10,7)
    "destination_lng": 73.8567400,                 // required, decimal (10,7)
    "optimized_path": [                            // optional, JSON (any structure)
        {"lat": 19.076, "lng": 72.877},
        {"lat": 18.52, "lng": 73.856}
    ],
    "total_distance_km": 150.50,                   // optional, decimal
    "estimated_duration_min": 180                   // optional, integer
}
```

### PUT `/api/v1/trips/routes/{id}/` — Full Update Route
**Auth:** Bearer Token
> Same fields as POST.

### PATCH `/api/v1/trips/routes/{id}/` — Partial Update Route
**Auth:** Bearer Token
```json
{
    "total_distance_km": 155.25,
    "estimated_duration_min": 195
}
```

### POST `/api/v1/trips/routes/{id}/approve/` — Approve Route
**Auth:** Bearer Token (fleet_manager only)
```json
{}
```
> No body required. Sets `approved_by` and `approved_at` automatically.

### DELETE `/api/v1/trips/routes/{id}/` — Delete Route
**Auth:** Bearer Token

---

## 14. Route Deviations

**Permission:** Any authenticated user.

### GET `/api/v1/trips/route-deviations/` — List Deviations
**Auth:** Bearer Token
**Filters:** `?trip=1`

### GET `/api/v1/trips/route-deviations/{id}/` — Get Deviation Detail
**Auth:** Bearer Token

### POST `/api/v1/trips/route-deviations/` — Create Deviation
**Auth:** Bearer Token
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
**Auth:** Bearer Token
```json
{
    "resolved_at": "2024-06-15T10:30:00Z"
}
```

### DELETE `/api/v1/trips/route-deviations/{id}/` — Delete Deviation
**Auth:** Bearer Token

---

## 15. GPS Logs

**Permission:** Any authenticated user.

### GET `/api/v1/trips/gps-logs/` — List GPS Logs
**Auth:** Bearer Token
**Filters:** `?trip=1` `?vehicle=1`
**Ordering:** `?ordering=-recorded_at`

### GET `/api/v1/trips/gps-logs/{id}/` — Get GPS Log Detail
**Auth:** Bearer Token

### POST `/api/v1/trips/gps-logs/` — Create GPS Log
**Auth:** Bearer Token
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
**Auth:** Bearer Token
> Same fields as POST.

### PATCH `/api/v1/trips/gps-logs/{id}/` — Partial Update
**Auth:** Bearer Token
```json
{
    "speed_kmh": 50.00
}
```

### DELETE `/api/v1/trips/gps-logs/{id}/` — Delete GPS Log
**Auth:** Bearer Token

---

## 16. Driver Locations (Live Tracking)

**Permission:** Any authenticated user can read. Only **drivers** can update their location.

Driver locations store the **current** position of a driver on a given trip. Unlike GPS Logs (which keep a full history), this table maintains **one row per trip + driver** — creating it on the first call and updating it on subsequent calls (upsert).

When a driver updates their location via the REST endpoint, the update is also **broadcast to the WebSocket room** (`ws/trips/{trip_id}/gps/`) so fleet managers watching that trip receive the update in real time.

### GET `/api/v1/trips/driver-locations/` — List Driver Locations
**Auth:** Bearer Token
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
**Auth:** Bearer Token

---

### POST `/api/v1/trips/driver-locations/update_location/` — Upsert Driver Location
**Auth:** Bearer Token (Driver only)

This is the primary endpoint called from the **driver's phone**. It creates a new location entry the first time a driver reports for a trip, and updates the existing entry on all subsequent calls for the same trip + driver.

```json
{
    "trip_id": 1,                      // required, FK → Trip ID (must be in_progress, assigned to this driver)
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

**Error (404):** Trip not found.
**Error (403):** Authenticated user is not the driver for this trip.
**Error (400):** Trip is not in `in_progress` status.

> **Side effects:**
> - Upserts a row in the `driver_locations` table (one row per trip + driver).
> - Broadcasts the location update to the WebSocket channel group `trip_{trip_id}_tracking`, so any fleet manager connected to `ws/trips/{trip_id}/gps/` receives the update instantly.

---

## 17. Geofence Events

**Permission:** Any authenticated user. **READ-ONLY** endpoint.

### GET `/api/v1/trips/geofence-events/` — List Events
**Auth:** Bearer Token
**Filters:** `?trip=1` `?vehicle=1` `?geofence=1` `?event_type=entry`

### GET `/api/v1/trips/geofence-events/{id}/` — Get Event Detail
**Auth:** Bearer Token

---

## 18. Trip Expenses

**Permission:** Any authenticated user.
**Note:** `driver` is auto-set to the logged-in user.

### GET `/api/v1/trips/expenses/` — List Expenses
**Auth:** Bearer Token
**Filters:** `?trip=1` `?driver=1` `?expense_type=fuel`

### GET `/api/v1/trips/expenses/{id}/` — Get Expense Detail
**Auth:** Bearer Token

### POST `/api/v1/trips/expenses/` — Create Expense
**Auth:** Bearer Token
```json
{
    "trip": 1,                         // required, FK → Trip ID
    "expense_type": "fuel",            // required: "fuel"|"toll"|"parking"|"other"
    "amount": 2500.00,                 // required, decimal (10,2)
    "currency": "INR",                 // optional (default: "INR"), max 3 chars
    "description": "Diesel refill at HP station", // optional
    "receipt_url": "https://example.com/receipt.jpg" // optional, valid URL
}
```

### PUT `/api/v1/trips/expenses/{id}/` — Full Update
**Auth:** Bearer Token
> Same fields as POST (driver remains auto-set).

### PATCH `/api/v1/trips/expenses/{id}/` — Partial Update
**Auth:** Bearer Token
```json
{
    "amount": 2750.00,
    "description": "Updated amount after verification"
}
```

### DELETE `/api/v1/trips/expenses/{id}/` — Delete Expense
**Auth:** Bearer Token

---

## 19. Fuel Logs

**Permission:** Any authenticated user.
**Note:** `driver` is auto-set to the logged-in user on creation.

### GET `/api/v1/trips/fuel-logs/` — List Fuel Logs
**Auth:** Bearer Token
**Filters:** `?trip=1` `?vehicle=1` `?driver=1`

### GET `/api/v1/trips/fuel-logs/{id}/` — Get Fuel Log Detail
**Auth:** Bearer Token

### POST `/api/v1/trips/fuel-logs/` — Create Fuel Log
**Auth:** Bearer Token
```json
{
    "trip": 1,                         // required, FK → Trip ID
    "vehicle": 1,                      // required, FK → Vehicle ID
    "fuel_amount_liters": 50.00,       // required, decimal (8,2)
    "cost_per_liter": 95.50,           // optional, decimal (8,2)
    "total_cost": 4775.00,             // required, decimal (10,2)
    "odometer_km": 15250.00,           // optional, decimal (10,2)
    "fuel_station": "HP Petrol Pump, Highway NH4", // optional, max 200
    "receipt_url": "https://example.com/fuel.jpg"  // optional, valid URL
}
```

### PUT `/api/v1/trips/fuel-logs/{id}/` — Full Update
**Auth:** Bearer Token
> Same fields as POST.

### PATCH `/api/v1/trips/fuel-logs/{id}/` — Partial Update
**Auth:** Bearer Token
```json
{
    "total_cost": 4800.00
}
```

### DELETE `/api/v1/trips/fuel-logs/{id}/` — Delete Fuel Log
**Auth:** Bearer Token

---

## 20. Delivery Proofs

**Permission:** Any authenticated user.
**Note:** `driver` is auto-set to the logged-in user.

### GET `/api/v1/trips/delivery-proofs/` — List Delivery Proofs
**Auth:** Bearer Token

### GET `/api/v1/trips/delivery-proofs/{id}/` — Get Proof Detail
**Auth:** Bearer Token

### POST `/api/v1/trips/delivery-proofs/` — Create Delivery Proof
**Auth:** Bearer Token
> Use `multipart/form-data` if uploading `file_url`.
```json
{
    "drop_point": 1,                           // required, FK → OrderDropPoint ID
    "trip": 1,                                 // required, FK → Trip ID
    "proof_type": "photo",                     // required: "photo"|"signature"|"digital_confirmation"
    "file_url": "<file upload>",               // optional, file upload (multipart/form-data)
    "digital_confirmation_code": "",           // optional, max 100
    "latitude": 18.5204300,                    // optional, decimal (10,7)
    "longitude": 73.8567400                    // optional, decimal (10,7)
}
```

### PUT `/api/v1/trips/delivery-proofs/{id}/` — Full Update
**Auth:** Bearer Token
> Same fields as POST.

### PATCH `/api/v1/trips/delivery-proofs/{id}/` — Partial Update
**Auth:** Bearer Token
```json
{
    "digital_confirmation_code": "CONF-12345"
}
```

### DELETE `/api/v1/trips/delivery-proofs/{id}/` — Delete Proof
**Auth:** Bearer Token

---

## 21. Maintenance Schedules

**Permission:** Maintenance Staff or Fleet Manager only.
**Note:** `scheduled_by` is auto-set to the logged-in user.

### GET `/api/v1/maintenance/schedules/` — List Schedules
**Auth:** Bearer Token
**Filters:** `?vehicle=1` `?maintenance_type=preventive` `?status=scheduled` `?scheduled_date=2024-06-15`
**Ordering:** `?ordering=scheduled_date`

### GET `/api/v1/maintenance/schedules/{id}/` — Get Schedule Detail
**Auth:** Bearer Token

### POST `/api/v1/maintenance/schedules/` — Create Schedule
**Auth:** Bearer Token (maintenance_staff or fleet_manager)
```json
{
    "vehicle": 1,                              // required, FK → Vehicle ID
    "maintenance_type": "preventive",          // required: "preventive"|"corrective"|"emergency"
    "description": "Regular 10K km service",   // required, text
    "scheduled_date": "2024-07-01",            // required, date YYYY-MM-DD
    "estimated_duration_hours": 4.00,          // optional, decimal (5,2)
    "status": "scheduled",                     // optional: "scheduled"|"in_progress"|"completed"|"cancelled"
    "notes": "Include oil change and filter replacement" // optional
}
```

### PUT `/api/v1/maintenance/schedules/{id}/` — Full Update
**Auth:** Bearer Token (maintenance_staff or fleet_manager)
> Same fields as POST.

### PATCH `/api/v1/maintenance/schedules/{id}/` — Partial Update
**Auth:** Bearer Token (maintenance_staff or fleet_manager)
```json
{
    "status": "in_progress",
    "notes": "Started maintenance work"
}
```

### DELETE `/api/v1/maintenance/schedules/{id}/` — Delete Schedule
**Auth:** Bearer Token (maintenance_staff or fleet_manager)

---

## 22. Maintenance Records

**Permission:** Maintenance Staff or Fleet Manager only.
**Note:** `assigned_by` is auto-set to the logged-in user. Vehicle status is auto-set to `under_maintenance` on creation.

### GET `/api/v1/maintenance/records/` — List Records
**Auth:** Bearer Token
**Filters:** `?vehicle=1` `?maintenance_type=preventive` `?repair_status=pending` `?assigned_to=2`
**Ordering:** `?ordering=-created_at`

### GET `/api/v1/maintenance/records/{id}/` — Get Record Detail (includes spare_parts & parts_used)
**Auth:** Bearer Token

**Response includes:**
```json
{
    "id": 1,
    "vehicle": 1,
    "schedule": null,
    "issue": null,
    "maintenance_type": "corrective",
    "description": "Brake pad replacement",
    "repair_status": "pending",
    "assigned_to": 3,
    "assigned_by": 2,
    "started_at": null,
    "completed_at": null,
    "total_cost": null,
    "mileage_at_service": "15500.00",
    "technician_notes": "",
    "parts_used": [
        {"name": "Brake Pad Set", "part_number": "BP-TT-001", "quantity": 2, "unit_cost": 1500.00},
        {"name": "Brake Fluid",   "part_number": "BF-DOT4",   "quantity": 1, "unit_cost": 350.00}
    ],
    "spare_parts": [...],
    "created_at": "2026-03-26T09:00:00Z",
    "updated_at": "2026-03-26T09:00:00Z"
}
```

### POST `/api/v1/maintenance/records/` — Create Maintenance Record
**Auth:** Bearer Token (maintenance_staff or fleet_manager)
```json
{
    "vehicle": 1,                              // required, FK → Vehicle ID
    "schedule": 1,                             // optional, FK → MaintenanceSchedule ID
    "issue": 1,                                // optional, FK → VehicleIssue ID
    "maintenance_type": "corrective",          // required: "preventive"|"corrective"|"emergency"
    "description": "Brake pad replacement",    // required, text
    "assigned_to": 3,                          // optional, FK → User ID (maintenance_staff)
    "mileage_at_service": 15500.00,            // optional, decimal (10,2)
    "technician_notes": "Front and rear pads replaced", // optional
    "parts_used": [                            // optional, JSON array — free-form part objects
        {"name": "Brake Pad Set", "part_number": "BP-TT-001", "quantity": 2, "unit_cost": 1500.00},
        {"name": "Brake Fluid",   "part_number": "BF-DOT4",   "quantity": 1, "unit_cost": 350.00}
    ],
    "spare_parts": [                           // optional, creates SparePartUsed rows (structured)
        {
            "part_name": "Brake Pad Set",      // required, max 200
            "part_number": "BP-TT-001",        // optional, max 100
            "quantity": 2.00,                   // required, decimal (10,2)
            "unit_cost": 1500.00               // optional, decimal (10,2)
        }
    ]
}
```
> `parts_used` is a **JSON array stored directly on the record** — use it to store a snapshot of parts in any shape your frontend finds convenient.  
> `spare_parts` creates linked `SparePartUsed` rows (structured, relational).  
> `total_cost` for each spare part is auto-calculated as `quantity × unit_cost`.

### PUT `/api/v1/maintenance/records/{id}/` — Full Update
**Auth:** Bearer Token (maintenance_staff or fleet_manager)
```json
{
    "vehicle": 1,
    "schedule": 1,
    "issue": 1,
    "maintenance_type": "corrective",
    "description": "Brake pad replacement - full set",
    "repair_status": "pending",
    "assigned_to": 3,
    "mileage_at_service": 15500.00,
    "technician_notes": "Updated notes",
    "total_cost": 3350.00,
    "parts_used": [
        {"name": "Brake Pad Set", "part_number": "BP-TT-001", "quantity": 2, "unit_cost": 1500.00}
    ]
}
```

### PATCH `/api/v1/maintenance/records/{id}/` — Partial Update
**Auth:** Bearer Token (maintenance_staff or fleet_manager)
```json
{
    "technician_notes": "Completed - parts performing well",
    "total_cost": 3500.00,
    "parts_used": [
        {"name": "Brake Fluid", "part_number": "BF-DOT4", "quantity": 1, "unit_cost": 350.00}
    ]
}
```

### POST `/api/v1/maintenance/records/{id}/start_repair/` — Start Repair
**Auth:** Bearer Token (maintenance_staff or fleet_manager)
**Precondition:** `repair_status` must be `pending`
```json
{}
```
> No body required. Sets `repair_status` to `in_progress` and `started_at` to now.

### POST `/api/v1/maintenance/records/{id}/complete_repair/` — Complete Repair
**Auth:** Bearer Token (maintenance_staff or fleet_manager)
**Precondition:** `repair_status` must be `in_progress`
```json
{
    "total_cost": 3500.00,                     // optional (overrides existing)
    "technician_notes": "All work completed",  // optional (overrides existing)
    "parts_used": [                            // optional (overrides existing)
        {"name": "Brake Pad Set", "part_number": "BP-TT-001", "quantity": 2, "unit_cost": 1500.00},
        {"name": "Brake Fluid",   "part_number": "BF-DOT4",   "quantity": 1, "unit_cost": 350.00}
    ]
}
```
> Sets `repair_status=completed`, `completed_at=now`, vehicle `status=available`, updates `last_service_date`. If linked schedule → marks completed. If linked issue → marks resolved.

### DELETE `/api/v1/maintenance/records/{id}/` — Delete Record
**Auth:** Bearer Token (maintenance_staff or fleet_manager)


---

## 23. Spare Parts

**Permission:** Maintenance Staff or Fleet Manager only.

> **Table:** `spare_parts` — This is the primary endpoint for spare part CRUD operations. Data is stored in and retrieved from the `spare_parts` table.
> **Note:** `quantity` and `unit_cost` are stored as text in the database (to support flexible input) but `total_cost` is auto-calculated as a decimal.

### GET `/api/v1/maintenance/spare-parts/` — List Spare Parts
**Auth:** Bearer Token
**Filters:** `?maintenance=1`

### GET `/api/v1/maintenance/spare-parts/{id}/` — Get Spare Part Detail
**Auth:** Bearer Token

### POST `/api/v1/maintenance/spare-parts/` — Add Spare Part
**Auth:** Bearer Token (maintenance_staff or fleet_manager)
```json
{
    "part_name": "Oil Filter",         // required, text
    "part_number": "OF-001",           // optional, text
    "quantity": "1",                   // optional, text (auto-used to calculate total_cost)
    "unit_cost": "250.00",             // optional, text (auto-used to calculate total_cost)
    "maintenance": 1                   // optional, FK → MaintenanceRecord ID (link to a record if needed)
}
```
> `maintenance` is fully optional — spare parts can exist independently.
> `total_cost` is auto-calculated as `float(quantity) × float(unit_cost)` when both are provided.

**Response:**
```json
{
    "id": 1,
    "maintenance": 1,
    "part_name": "Oil Filter",
    "part_number": "OF-001",
    "quantity": "1",
    "unit_cost": "250.00",
    "total_cost": "250.00",
    "created_at": "2026-03-25T10:00:00Z",
    "updated_at": "2026-03-25T10:00:00Z"
}
```

### PUT `/api/v1/maintenance/spare-parts/{id}/` — Full Update
**Auth:** Bearer Token (maintenance_staff or fleet_manager)
> Same fields as POST.

### PATCH `/api/v1/maintenance/spare-parts/{id}/` — Partial Update
**Auth:** Bearer Token (maintenance_staff or fleet_manager)
```json
{
    "quantity": "2",
    "unit_cost": "275.00"
}
```

### DELETE `/api/v1/maintenance/spare-parts/{id}/` — Delete Spare Part
**Auth:** Bearer Token (maintenance_staff or fleet_manager)

---

## 24. Messages

**Permission:** Any authenticated user. Only sees own sent/received messages.
**Note:** `sender` is auto-set to the logged-in user.

### GET `/api/v1/comms/messages/` — List Messages
**Auth:** Bearer Token
**Filters:** `?trip=1` `?is_read=false` `?peer=2` (show conversation with user 2)
**Ordering:** `?ordering=-sent_at`

### GET `/api/v1/comms/messages/{id}/` — Get Message Detail
**Auth:** Bearer Token

### POST `/api/v1/comms/messages/` — Send Message
**Auth:** Bearer Token
```json
{
    "receiver": 2,                     // required, FK → User ID
    "trip": 1,                         // optional, FK → Trip ID
    "content": "Please confirm pickup at warehouse" // required, text
}
```

### PUT `/api/v1/comms/messages/{id}/` — Full Update Message
**Auth:** Bearer Token
```json
{
    "receiver": 2,
    "trip": 1,
    "content": "Updated message content"
}
```

### PATCH `/api/v1/comms/messages/{id}/` — Partial Update
**Auth:** Bearer Token
```json
{
    "content": "Corrected message"
}
```

### POST `/api/v1/comms/messages/{id}/mark_read/` — Mark Message as Read
**Auth:** Bearer Token (only the receiver can mark as read)
```json
{}
```
> No body required.

### POST `/api/v1/comms/messages/mark_all_read/` — Mark All Messages as Read
**Auth:** Bearer Token
```json
{}
```
> No body required. Returns count of messages marked.

### DELETE `/api/v1/comms/messages/{id}/` — Delete Message
**Auth:** Bearer Token

---

## 25. Notifications

**Permission:** Any authenticated user. Only sees own notifications.

### GET `/api/v1/comms/notifications/` — List Notifications
**Auth:** Bearer Token
**Filters:** `?alert_type=sos` `?status=unread` `?reference_type=trip`
**Ordering:** `?ordering=-created_at`

### GET `/api/v1/comms/notifications/{id}/` — Get Notification Detail
**Auth:** Bearer Token

### POST `/api/v1/comms/notifications/` — Create Notification
**Auth:** Bearer Token
```json
{
    "alert_type": "maintenance_due",           // required: "sos"|"route_deviation"|"geofence_entry"|"geofence_exit"|"maintenance_due"|"issue_reported"|"trip_rejected"|"leave_request"|"leave_approved"|"leave_rejected"
    "title": "Vehicle MH12AB1234 service due", // required, max 255
    "body": "Current mileage approaching next service threshold", // optional
    "status": "unread",                        // optional: "unread"|"read" (default: "unread")
    "reference_id": 1,                         // optional, integer (e.g., vehicle ID)
    "reference_type": "vehicle"                // optional, max 50 (e.g., "vehicle", "trip")
}
```

### PATCH `/api/v1/comms/notifications/{id}/` — Partial Update
**Auth:** Bearer Token
```json
{
    "status": "read"
}
```

### POST `/api/v1/comms/notifications/{id}/mark_read/` — Mark Notification as Read
**Auth:** Bearer Token
```json
{}
```
> No body required.

### POST `/api/v1/comms/notifications/mark_all_read/` — Mark All as Read
**Auth:** Bearer Token
```json
{}
```
> No body required. Returns count marked.

### GET `/api/v1/comms/notifications/unread_count/` — Get Unread Count
**Auth:** Bearer Token
**Response:**
```json
{
    "unread_count": 5
}
```

### DELETE `/api/v1/comms/notifications/{id}/` — Delete Notification
**Auth:** Bearer Token

---

## 26. SOS Alerts

**Permission:** Any authenticated user.
**Note:** `driver` is auto-set to the logged-in user.

### GET `/api/v1/comms/sos-alerts/` — List SOS Alerts
**Auth:** Bearer Token
**Filters:** `?driver=1` `?vehicle=1` `?resolved=false`
**Ordering:** `?ordering=-triggered_at`

### GET `/api/v1/comms/sos-alerts/{id}/` — Get SOS Alert Detail
**Auth:** Bearer Token

### POST `/api/v1/comms/sos-alerts/` — Trigger SOS Alert
**Auth:** Bearer Token
```json
{
    "vehicle": 1,                      // required, FK → Vehicle ID
    "trip": 1,                         // optional, FK → Trip ID
    "latitude": 19.0760000,           // required, decimal (10,7)
    "longitude": 72.8777000,          // required, decimal (10,7)
    "message": "Accident on highway, need help immediately" // optional
}
```

### PATCH `/api/v1/comms/sos-alerts/{id}/` — Partial Update
**Auth:** Bearer Token
```json
{
    "message": "Updated situation: minor collision, no injuries"
}
```

### POST `/api/v1/comms/sos-alerts/{id}/resolve/` — Resolve SOS Alert
**Auth:** Bearer Token (fleet_manager only)
```json
{}
```
> No body required. Sets `resolved=true`, `resolved_by=current_user`, `resolved_at=now`.

### DELETE `/api/v1/comms/sos-alerts/{id}/` — Delete SOS Alert
**Auth:** Bearer Token

---

## 27. WebSocket Endpoints

**Protocol:** `ws://` (or `wss://` for production)
**Auth:** Pass JWT token as query parameter: `?token=<access_token>`

### GPS Live Tracking
```
ws://localhost:8000/ws/trips/{trip_id}/gps/?token=<access_token>
```

**How it works:**
- Both drivers and fleet managers connect to the same WebSocket room for a trip.
- **Drivers** can send GPS data via WebSocket (saved to `gps_logs` table, broadcast to room).
- **Fleet managers** connect to the room to receive real-time location updates.
- Location updates sent via the REST endpoint (`POST /api/v1/trips/driver-locations/update_location/`) are also broadcast to this room, so fleet managers receive updates regardless of whether the driver uses WebSocket or REST.

**Send (Driver → Server, JSON):**
```json
{
    "latitude": 19.0760000,
    "longitude": 72.8777000,
    "speed_kmh": 45.5,
    "heading_deg": 180.0
}
```

**Receive (Server → Fleet Manager, JSON):**
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

### Notifications
```
ws://localhost:8000/ws/notifications/?token=<access_token>
```
> Receives real-time notifications pushed from server.

### Chat
```
ws://localhost:8000/ws/chat/{trip_id}/?token=<access_token>
```
**Send (JSON):**
```json
{
    "message": "Reached the first drop point"
}
```

---

## 28. Driver Availability — Clock-In & Clock-Out

**Permission:** Any authenticated user (intended for drivers).

Drivers have a `driver_status` on their profile that the fleet manager uses to track field availability. This status is managed via the clock-in/out endpoints and is automatically synced when a trip starts or completes.

### Driver Status Values

| Value | Meaning |
|---|---|
| `clocked_out` | Driver is off duty. Default on registration. |
| `available` | Driver is on duty and ready for a trip. |
| `in_trip` | Driver is actively executing a trip. |
| `on_rest` | Driver completed a trip and is in a mandatory 9-hour rest period. Auto-reverts to `available` when rest ends. |
| `on_leave` | Driver is on approved leave. Set by fleet manager approving a leave request. |

> `driver_status` is visible on every user/profile response via `profile.driver_status`.
> `rest_ends_at` is set to `trip.ended_at + 9 hours` when status becomes `on_rest`. It is cleared when status reverts to `available`.
>
> **Lazy revert:** There is no background job. When a driver whose `driver_status=on_rest` calls `GET /auth/me/` and `rest_ends_at <= now`, the server automatically flips their status to `available` before returning the response.

---

### POST `/api/v1/auth/clock-in/` — Driver Clock In
**Auth:** Bearer Token  
**Body:** *(none required)*

**Response (200):**
```json
{
    "driver_status": "available",
    "detail": "Clocked in successfully. You are now available."
}
```
**Error (400):** If `driver_status` is currently `in_trip`:
```json
{
    "detail": "Cannot clock in while on an active trip. Complete the trip first."
}
```
**Error (400):** If `driver_status` is currently `on_leave`:
```json
{
    "detail": "Cannot clock in while on approved leave."
}
```
> **Side effect:** Sets `profile.driver_status = 'available'`. Idempotent if already `available`.

---

### POST `/api/v1/auth/clock-out/` — Driver Clock Out
**Auth:** Bearer Token  
**Body:** *(none required)*

**Response (200):**
```json
{
    "driver_status": "clocked_out",
    "detail": "Clocked out successfully. You are now unavailable."
}
```
**Error (400):** If `driver_status` is currently `in_trip`:
```json
{
    "detail": "Cannot clock out while on an active trip. Complete the trip first."
}
```
> **Side effect:** Sets `profile.driver_status = 'clocked_out'`. Idempotent if already `clocked_out`.

---

### Automatic Status Transitions via Trip Lifecycle

| Trigger | Endpoint | `driver_status` → | Notes |
|---|---|---|---|
| Driver accepts trip | `POST /trips/trips/{id}/accept/` | `in_trip` | Also sets `started_at` |
| Driver starts trip | `POST /trips/trips/{id}/start/` | `in_trip` | Also sets `started_at` |
| Driver completes trip | `POST /trips/trips/{id}/complete/` | `on_rest` | Sets `rest_ends_at = ended_at + 9h` |
| Driver rejects trip | `POST /trips/trips/{id}/reject/` | *(unchanged)* | Trip reverts to `pending`, notifies managers |
| Trip cancelled | `POST /trips/trips/{id}/cancel/` | `available` | |
| Leave approved | `POST /leave-requests/{id}/approve/` | `on_leave` | Set by fleet manager |
| Leave rejected | `POST /leave-requests/{id}/reject/` | *(unchanged)* | Notifies driver |

---

### Filter Drivers by Availability (Fleet Manager)

```
GET /api/v1/users/?profile__driver_status=available
GET /api/v1/users/?profile__driver_status=in_trip
GET /api/v1/users/?profile__driver_status=clocked_out
GET /api/v1/users/?profile__driver_status=on_rest
GET /api/v1/users/?profile__driver_status=on_leave
```
> Combine with `?profile__role=driver` to scope to drivers only.

---

## 29. Driver Documents

**Permission:** Any authenticated user.
**Note:** `user` is auto-set to the logged-in user. Drivers see only their own documents; fleet managers see all.
**Content-Type:** `multipart/form-data` (file upload)
**Upload directory:** `media/driver_documents/`

> **Profile integration:** After uploading documents, the absolute URLs are exposed in the `GET /auth/me/` and `GET /users/{id}/` responses under `profile.driving_licence` and `profile.aadhaar_card`. These are the latest uploaded files for each type.

### GET `/api/v1/driver-documents/` — List Driver Documents
**Auth:** Bearer Token
**Filters:** `?document_type=aadhar` `?user=<id>` (fleet manager only)

### GET `/api/v1/driver-documents/{id}/` — Get Document Detail
**Auth:** Bearer Token

### POST `/api/v1/driver-documents/` — Upload Driver Document
**Auth:** Bearer Token
**Content-Type:** `multipart/form-data`
```
document_type: aadhar          // required: "aadhar"|"driving_license"
file: <binary file>            // required, file upload (image or PDF)
```

### PATCH `/api/v1/driver-documents/{id}/` — Update Document
**Auth:** Bearer Token
```
file: <binary file>            // replace the file
```

### DELETE `/api/v1/driver-documents/{id}/` — Delete Document
**Auth:** Bearer Token

---

## 30. Profile Images

**Permission:** Any authenticated user.
**Note:** `user` is auto-set to the logged-in user. Each user can have only one profile image (OneToOne). Drivers see only their own; fleet managers see all.
**Content-Type:** `multipart/form-data` (file upload)
**Upload directory:** `media/profile_images/`

### GET `/api/v1/profile-images/` — List Profile Images
**Auth:** Bearer Token

### GET `/api/v1/profile-images/{id}/` — Get Profile Image Detail
**Auth:** Bearer Token

### POST `/api/v1/profile-images/` — Upload Profile Image
**Auth:** Bearer Token
**Content-Type:** `multipart/form-data`
```
image: <binary image file>     // required, image upload
```

### PATCH `/api/v1/profile-images/{id}/` — Update Profile Image
**Auth:** Bearer Token
```
image: <binary image file>     // replace with new image
```

### DELETE `/api/v1/profile-images/{id}/` — Delete Profile Image
**Auth:** Bearer Token

---

## 31. Odometer Images

**Permission:** Any authenticated user.
**Note:** `driver` is auto-set to the logged-in user.
**Content-Type:** `multipart/form-data` (file upload)
**Upload directory:** `media/odometer_images/`

### GET `/api/v1/trips/odometer-images/` — List Odometer Images
**Auth:** Bearer Token
**Filters:** `?trip=1` `?vehicle=1` `?driver=1`

### GET `/api/v1/trips/odometer-images/{id}/` — Get Odometer Image Detail
**Auth:** Bearer Token

### POST `/api/v1/trips/odometer-images/` — Upload Odometer Image
**Auth:** Bearer Token
**Content-Type:** `multipart/form-data`
```
trip: 1                          // required, FK → Trip ID
vehicle: 1                       // required, FK → Vehicle ID
image: <binary image file>       // required, image upload
odometer_reading_km: 15250.00    // optional, decimal (10,2)
```

### PATCH `/api/v1/trips/odometer-images/{id}/` — Update Odometer Image
**Auth:** Bearer Token

### DELETE `/api/v1/trips/odometer-images/{id}/` — Delete Odometer Image
**Auth:** Bearer Token

---

## 32. Leave Requests

**Permission:** Any authenticated user.
- **Drivers** can create leave requests and see only their own.
- **Fleet Managers** can see all leave requests and approve/reject them.
**Note:** `driver` is auto-set to the logged-in user on creation.

### GET `/api/v1/leave-requests/` — List Leave Requests
**Auth:** Bearer Token
**Filters:** `?status=pending` `?driver=<id>` (fleet manager only)

### GET `/api/v1/leave-requests/{id}/` — Get Leave Request Detail
**Auth:** Bearer Token

### POST `/api/v1/leave-requests/` — Submit Leave Request (Driver)
**Auth:** Bearer Token
```json
{
    "start_date": "2026-04-01",        // required, date YYYY-MM-DD
    "end_date": "2026-04-05",          // required, date YYYY-MM-DD
    "reason": "Family function"        // optional, text
}
```
**Response (201):**
```json
{
    "id": 1,
    "driver": 2,
    "driver_name": "John Doe",
    "start_date": "2026-04-01",
    "end_date": "2026-04-05",
    "reason": "Family function",
    "status": "pending",
    "reviewed_by": null,
    "reviewed_at": null,
    "rejection_reason": "",
    "created_at": "2026-03-25T10:00:00Z",
    "updated_at": "2026-03-25T10:00:00Z"
}
```

> **Side effect on create:** Sends a `leave_request` notification to all fleet managers.

### PUT `/api/v1/leave-requests/{id}/` — Full Update (Driver, own pending requests only)
**Auth:** Bearer Token
> Same fields as POST. Only `pending` requests can be edited.

### PATCH `/api/v1/leave-requests/{id}/` — Partial Update
**Auth:** Bearer Token
```json
{
    "reason": "Updated reason"
}
```

### DELETE `/api/v1/leave-requests/{id}/` — Delete Leave Request
**Auth:** Bearer Token (driver can delete own pending requests; fleet manager can delete any)

---

### POST `/api/v1/leave-requests/{id}/approve/` — Approve Leave Request (Fleet Manager)
**Auth:** Bearer Token (fleet_manager only)
**Precondition:** Request status must be `pending`
```json
{}
```
> No body required.

**Response (200):** Full leave request object with `"status": "approved"`.

> **Side effects:**
> - Sets leave request `status=approved`, `reviewed_by=current_user`, `reviewed_at=now`.
> - Sets driver's `driver_status=on_leave`.
> - Sends a `leave_approved` notification to the driver.

---

### POST `/api/v1/leave-requests/{id}/reject/` — Reject Leave Request (Fleet Manager)
**Auth:** Bearer Token (fleet_manager only)
**Precondition:** Request status must be `pending`
```json
{
    "rejection_reason": "Insufficient leave balance"   // optional, text
}
```

**Response (200):** Full leave request object with `"status": "rejected"`.

> **Side effects:**
> - Sets leave request `status=rejected`, `reviewed_by=current_user`, `reviewed_at=now`, `rejection_reason=<reason>`.
> - Driver's `driver_status` is **not** changed.
> - Sends a `leave_rejected` notification to the driver with the rejection reason.

---

## 33. Spare Parts Used (Legacy)

**Permission:** Maintenance Staff or Fleet Manager only.

> **Table:** `spare_parts_used` — Legacy table. New integrations should use `/maintenance/spare-parts/` (Section 23) which operates on the `spare_parts` table. This endpoint is kept for backwards compatibility.

### GET `/api/v1/maintenance/spare-parts-used/` — List Spare Parts Used
**Auth:** Bearer Token
**Filters:** `?maintenance=1`

### GET `/api/v1/maintenance/spare-parts-used/{id}/` — Get Spare Part Used Detail
**Auth:** Bearer Token

### POST `/api/v1/maintenance/spare-parts-used/` — Add Spare Part Used
**Auth:** Bearer Token (maintenance_staff or fleet_manager)
```json
{
    "maintenance": 1,                  // required, FK → MaintenanceRecord ID
    "part_name": "Oil Filter",         // required, max 200
    "part_number": "OF-001",           // optional, max 100
    "quantity": 1.00,                  // required, decimal (10,2)
    "unit_cost": 250.00                // optional, decimal (10,2)
}
```
> `total_cost` is auto-calculated as `quantity × unit_cost`.

### PUT `/api/v1/maintenance/spare-parts-used/{id}/` — Full Update
**Auth:** Bearer Token (maintenance_staff or fleet_manager)
> Same fields as POST.

### PATCH `/api/v1/maintenance/spare-parts-used/{id}/` — Partial Update
**Auth:** Bearer Token (maintenance_staff or fleet_manager)
```json
{
    "quantity": 2.00,
    "unit_cost": 275.00
}
```

### DELETE `/api/v1/maintenance/spare-parts-used/{id}/` — Delete Spare Part Used
**Auth:** Bearer Token (maintenance_staff or fleet_manager)

---

## Quick Reference: Pagination

All list endpoints use page-number pagination:
```
?page=1&page_size=25
```
Default page size: **25**

Response format:
```json
{
    "count": 100,
    "next": "http://localhost:8000/api/v1/.../&page=2",
    "previous": null,
    "results": [...]
}
```

---

## Quick Reference: Auth Header

For all authenticated requests in Postman:

| Key             | Value                        |
|-----------------|------------------------------|
| Authorization   | Bearer `<access_token>`      |

Set this in Postman → **Headers** tab, or use **Authorization** tab → Type: **Bearer Token**.

---

## Quick Reference: Testing Workflow

1. **Register** users with different roles (driver, fleet_manager, maintenance_staff)
2. **Login** → save the `access` token
3. **Create Locations** (as fleet_manager) — at least one warehouse
4. **Create Geofences** (as fleet_manager) — around key locations
5. **Create Vehicles** (as fleet_manager)
6. **Create Inspection Checklists + Items** (as maintenance_staff/fleet_manager)
7. **Create Orders** (as fleet_manager) — with drop points
8. **Create Trips** (as fleet_manager) — assign vehicle + driver → trip status is `assigned`
9. **Accept Trip** (as driver) → trip goes `in_progress` + driver goes `in_trip`
   - Or **Reject Trip** → trip reverts to `pending`, fleet manager gets notification
10. **Update Driver Location** → **Log GPS** → **Complete Trip** (as driver) → driver goes `on_rest` for 9 hours
11. **Submit Inspections** (as driver) — pre/post trip
12. **Report Issues** (as driver) → **Create Maintenance Records** (as maintenance_staff)
13. **Send Messages** / **Trigger SOS** (as driver)
14. **Resolve SOS** (as fleet_manager)
15. **Submit Leave Request** (as driver) → fleet manager gets notification
16. **Approve/Reject Leave** (as fleet_manager) → driver status → `on_leave` or unchanged
17. **Upload Driver Documents** (as driver) → `POST /driver-documents/` → check `GET /auth/me/` for `profile.driving_licence` / `profile.aadhaar_card` URLs

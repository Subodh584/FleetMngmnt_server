# Inspection Flow — Client Developer Guide

This document is the complete reference for every inspection-related API endpoint in the Fleet Management system. It covers the full lifecycle: checklists, submitting inspections, raising issues, and the fleet manager review workflow.

All requests require a valid JWT access token unless stated otherwise.

```
Authorization: Bearer <access_token>
Content-Type: application/json
```

Base URL: `https://<your-domain>/api/v1`

---

## Table of Contents

1. [Roles & Permissions](#1-roles--permissions)
2. [Data Model Overview](#2-data-model-overview)
3. [Checklist Endpoints](#3-checklist-endpoints)
   - [GET pre_trip_default](#31-get-the-default-pre-trip-checklist-driver)
   - [GET inspection-checklists/](#32-list-all-checklists-fleet-manager--maintenance)
   - [GET inspection-checklists/:id/](#33-get-a-single-checklist)
4. [Inspection Endpoints](#4-inspection-endpoints)
   - [POST — Create Inspection](#41-create-an-inspection-driver)
   - [GET — List Inspections](#42-list-inspections)
   - [GET — Get Single Inspection](#43-get-a-single-inspection)
   - [POST — Review an Inspection](#44-review-an-inspection-fleet-manager--maintenance)
   - [GET — All Inspections for a Vehicle](#45-all-inspections-for-a-vehicle)
5. [Vehicle Issue Endpoints](#5-vehicle-issue-endpoints)
   - [POST — Raise an Issue](#51-raise-an-issue-driver)
   - [GET — List Issues](#52-list-issues)
   - [GET — Issue Detail](#53-issue-detail-view-fleet-manager)
   - [PATCH — Update Issue Status](#54-update-issue-status-fleet-manager--maintenance)
   - [GET — All Issues for a Vehicle](#55-all-issues-for-a-vehicle)
6. [Full Schemas](#6-full-schemas)
7. [Enum Reference](#7-enum-reference)
8. [Error Reference](#8-error-reference)
9. [Complete Flow Walkthrough](#9-complete-flow-walkthrough)

---

## 1. Roles & Permissions

| Role | Can do |
|------|--------|
| `driver` | Fetch checklists, submit inspections, raise issues, start/complete trips |
| `fleet_manager` | Everything drivers can + review inspections, manage issues, manage checklists |
| `maintenance_staff` | Review inspections, manage issues, manage checklists |

Endpoints marked **Fleet Manager / Maintenance** will return `403 Forbidden` if called by a driver.

---

## 2. Data Model Overview

Understanding how the pieces connect will make the API much easier to work with.

```
InspectionChecklist
  └── InspectionChecklistItem  (1 checklist → many items)
        └── InspectionResult   (1 item → many results, one per inspection)

Inspection
  ├── vehicle        (which vehicle was inspected)
  ├── driver         (who did the inspection, auto-set from token)
  ├── trip           (which trip this is linked to, set at trip-start)
  ├── checklist      (which template was used)
  ├── inspection_type  (pre_trip / post_trip / ad_hoc)
  ├── overall_status   (auto-calculated: approved / flagged)
  └── results[]      (one InspectionResult per checklist item)

VehicleIssue
  ├── vehicle
  ├── reported_by    (auto-set from token)
  └── inspection     (optional — the inspection that revealed the issue)
```

The key rule: **one API call creates the entire inspection** — you send all results in the same request body. You never need to create individual `InspectionResult` rows separately.

---

## 3. Checklist Endpoints

### 3.1 Get the Default Pre-Trip Checklist *(Driver)*

Use this at the start of the inspection screen to get the 5 checklist items and their IDs. **Save the `id` of each item** — you will need them in Section 4.1.

```
GET /api/v1/inspection-checklists/pre_trip_default/
```

**Permission:** Any authenticated user (driver, fleet_manager, maintenance_staff)

**Response `200 OK`**
```json
{
  "id": 1,
  "name": "Pre-Trip Inspection",
  "is_active": true,
  "created_at": "2026-03-17T10:00:00Z",
  "items": [
    { "id": 1, "checklist": 1, "item_name": "Tire Condition & Pressure",   "sequence_no": 1, "is_required": true },
    { "id": 2, "checklist": 1, "item_name": "Brake Condition & Response",  "sequence_no": 2, "is_required": true },
    { "id": 3, "checklist": 1, "item_name": "Lights & Blinkers",           "sequence_no": 3, "is_required": true },
    { "id": 4, "checklist": 1, "item_name": "Fuel Level",                  "sequence_no": 4, "is_required": true },
    { "id": 5, "checklist": 1, "item_name": "Engine Condition",            "sequence_no": 5, "is_required": true }
  ]
}
```

**Notes:**
- Items are always ordered by `sequence_no`. Render them in this order.
- `is_required: true` means the driver must check this item before submitting.
- If this returns `404`, the checklist has not been seeded — contact the backend team.

---

### 3.2 List All Checklists *(Fleet Manager / Maintenance)*

```
GET /api/v1/inspection-checklists/
```

**Permission:** `fleet_manager` or `maintenance_staff` only

**Query Parameters**

| Param | Example | Description |
|-------|---------|-------------|
| `is_active` | `?is_active=true` | Filter by active status |
| `search` | `?search=pre-trip` | Search by checklist name |

**Response `200 OK`** — Paginated list, same shape as 3.1 but multiple objects.

---

### 3.3 Get a Single Checklist

```
GET /api/v1/inspection-checklists/{id}/
```

**Permission:** `fleet_manager` or `maintenance_staff` only

Returns the same shape as [3.1](#31-get-the-default-pre-trip-checklist-driver).

---

## 4. Inspection Endpoints

### 4.1 Create an Inspection *(Driver)*

Submit a completed inspection in a single call. The backend automatically:
- Sets `driver` from the JWT token
- Calculates `overall_status` (`"approved"` if all pass/na, `"flagged"` if any fail)

```
POST /api/v1/inspections/
```

**Permission:** Any authenticated user

**Request Body**

```json
{
  "vehicle": 12,
  "checklist": 1,
  "inspection_type": "pre_trip",
  "notes": "Optional overall note about this inspection.",
  "results": [
    {
      "checklist_item_id": 1,
      "result": "pass",
      "notes": "",
      "photo_url": ""
    },
    {
      "checklist_item_id": 2,
      "result": "fail",
      "notes": "Squealing noise on heavy braking.",
      "photo_url": "https://storage.example.com/photos/brake-photo.jpg"
    },
    {
      "checklist_item_id": 3,
      "result": "pass"
    },
    {
      "checklist_item_id": 4,
      "result": "pass"
    },
    {
      "checklist_item_id": 5,
      "result": "pass"
    }
  ]
}
```

**Field Reference**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `vehicle` | integer | **Yes** | ID of the vehicle being inspected |
| `checklist` | integer | **Yes** | ID of the checklist (from Step 3.1) |
| `inspection_type` | string | **Yes** | `"pre_trip"`, `"post_trip"`, or `"ad_hoc"` |
| `notes` | string | No | General notes for the whole inspection |
| `trip` | integer | No | Trip ID — leave `null` here; the backend links it automatically when `POST /trips/{id}/start/` is called |
| `results` | array | **Yes** | One object per checklist item |
| `results[].checklist_item_id` | integer | **Yes** | The `id` from the items array in 3.1 |
| `results[].result` | string | **Yes** | `"pass"`, `"fail"`, or `"na"` |
| `results[].notes` | string | No | Notes specific to this item |
| `results[].photo_url` | string (URL) | No | Must be a valid URL if provided |

> You do **not** need to include all 5 items if some are `"na"`, but including all of them is recommended for a complete audit trail.

**Response `201 Created`**

```json
{
  "id": 47,
  "trip": null,
  "vehicle": 12,
  "driver": 3,
  "checklist": 1,
  "inspection_type": "pre_trip",
  "overall_status": "flagged",
  "notes": "Optional overall note about this inspection.",
  "reviewed_by": null,
  "reviewed_at": null,
  "submitted_at": "2026-03-17T08:30:00Z",
  "created_at": "2026-03-17T08:30:00Z",
  "results": [
    { "id": 201, "inspection": 47, "checklist_item": 1, "result": "pass", "notes": "",  "photo_url": "" },
    { "id": 202, "inspection": 47, "checklist_item": 2, "result": "fail", "notes": "Squealing noise on heavy braking.", "photo_url": "https://..." },
    { "id": 203, "inspection": 47, "checklist_item": 3, "result": "pass", "notes": "",  "photo_url": "" },
    { "id": 204, "inspection": 47, "checklist_item": 4, "result": "pass", "notes": "",  "photo_url": "" },
    { "id": 205, "inspection": 47, "checklist_item": 5, "result": "pass", "notes": "",  "photo_url": "" }
  ]
}
```

**`overall_status` is auto-set by the backend:**

| Condition | `overall_status` | What to show the driver |
|-----------|-----------------|-------------------------|
| All results are `"pass"` or `"na"` | `"approved"` | Enable "Start Trip" button |
| One or more results are `"fail"` | `"flagged"` | Disable "Start Trip", show "Notify Fleet Manager" |

> **Always save the `id` from this response.** It is the `inspection_id` needed to link this inspection to a trip and to raise an issue.

---

### 4.2 List Inspections

```
GET /api/v1/inspections/
```

**Permission:** Any authenticated user

**Query Parameters**

| Param | Example | Description |
|-------|---------|-------------|
| `vehicle` | `?vehicle=12` | Filter by vehicle ID |
| `driver` | `?driver=3` | Filter by driver ID |
| `inspection_type` | `?inspection_type=pre_trip` | Filter by type |
| `overall_status` | `?overall_status=flagged` | Filter by status |
| `ordering` | `?ordering=-submitted_at` | Sort field (prefix `-` for descending) |

**Response `200 OK`** — Paginated list of full inspection objects (same shape as 4.1 response).

---

### 4.3 Get a Single Inspection

```
GET /api/v1/inspections/{id}/
```

**Permission:** Any authenticated user

Returns the full inspection object including all nested `results`. Note that `results[].checklist_item` is just the ID here — to get the item name alongside the result, use the [Issue Detail endpoint](#53-issue-detail-view-fleet-manager) which nests the full inspection with item names.

---

### 4.4 Review an Inspection *(Fleet Manager / Maintenance)*

Allows a fleet manager or maintenance staff member to formally approve or flag an inspection after review. This sets `reviewed_by` and `reviewed_at` on the inspection.

```
POST /api/v1/inspections/{id}/review/
```

**Permission:** `fleet_manager` or `maintenance_staff` only

**Request Body**

```json
{ "overall_status": "approved" }
```

Accepted values: `"approved"` or `"flagged"` only. Any other value returns `400`.

**Response `200 OK`** — Full inspection object with `reviewed_by` and `reviewed_at` populated:

```json
{
  "id": 47,
  "overall_status": "approved",
  "reviewed_by": 7,
  "reviewed_at": "2026-03-17T09:15:00Z",
  ...
}
```

---

### 4.5 All Inspections for a Vehicle

Retrieve the complete inspection history for a specific vehicle, ordered newest first.

```
GET /api/v1/vehicles/{vehicle_id}/inspections/
```

**Permission:** Any authenticated user

**Response `200 OK`** — Paginated list of full inspection objects, ordered by `-submitted_at`.

---

## 5. Vehicle Issue Endpoints

### 5.1 Raise an Issue *(Driver)*

Called when the driver taps "Notify Fleet Manager" after a failed inspection. Always include the `inspection` ID so the fleet manager has full context.

```
POST /api/v1/vehicle-issues/
```

**Permission:** Any authenticated user

The `reported_by` field is **automatically set** from the JWT token — do not include it in the request.

**Request Body**

```json
{
  "vehicle": 12,
  "inspection": 47,
  "title": "Brake squealing — needs immediate check",
  "description": "Loud squealing noise on heavy braking. Could indicate worn brake pads.",
  "severity": "high",
  "photo_url": ""
}
```

**Field Reference**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `vehicle` | integer | **Yes** | ID of the vehicle |
| `inspection` | integer | No | Strongly recommended — ID from 4.1 response |
| `title` | string | **Yes** | Short summary (max 255 characters) |
| `description` | string | No | Detailed explanation |
| `severity` | string | **Yes** | `"low"`, `"medium"`, `"high"`, or `"critical"` |
| `photo_url` | string (URL) | No | Must be a valid URL if provided |

**Severity Guide**

| Value | When to use |
|-------|-------------|
| `"low"` | Cosmetic or minor issue, can be monitored |
| `"medium"` | Needs attention but not an immediate blocker |
| `"high"` | Significant safety or operational concern |
| `"critical"` | Vehicle must not depart — immediate repair required |

**Response `201 Created`**

```json
{
  "id": 15,
  "vehicle": 12,
  "reported_by": 3,
  "inspection": 47,
  "title": "Brake squealing — needs immediate check",
  "description": "Loud squealing noise on heavy braking...",
  "severity": "high",
  "status": "reported",
  "photo_url": "",
  "reported_at": "2026-03-17T08:33:00Z",
  "updated_at": "2026-03-17T08:33:00Z"
}
```

**What happens on the backend automatically:**
- Issue is saved with `status: "reported"`
- Every `fleet_manager` and `maintenance_staff` user immediately receives:
  - A database notification (`alert_type: "issue_reported"`, `reference_id: <issue_id>`)
  - A real-time WebSocket push to their notification channel

> After a successful `201`, disable the "Notify Fleet Manager" button to prevent duplicate reports for the same inspection.

---

### 5.2 List Issues

```
GET /api/v1/vehicle-issues/
```

**Permission:** Any authenticated user

**Query Parameters**

| Param | Example | Description |
|-------|---------|-------------|
| `vehicle` | `?vehicle=12` | Filter by vehicle ID |
| `reported_by` | `?reported_by=3` | Filter by driver ID |
| `severity` | `?severity=high` | Filter by severity level |
| `status` | `?status=reported` | Filter by issue status |
| `search` | `?search=brake` | Full-text search on title and description |
| `ordering` | `?ordering=-reported_at` | Sort field (prefix `-` for descending) |

**Response `200 OK`** — Paginated list (lightweight — foreign keys are IDs only):

```json
{
  "count": 5,
  "next": "https://...",
  "previous": null,
  "results": [
    {
      "id": 15,
      "vehicle": 12,
      "reported_by": 3,
      "inspection": 47,
      "title": "Brake squealing — needs immediate check",
      "severity": "high",
      "status": "reported",
      "photo_url": "",
      "reported_at": "2026-03-17T08:33:00Z",
      "updated_at": "2026-03-17T08:33:00Z"
    }
  ]
}
```

---

### 5.3 Issue Detail View *(Fleet Manager)*

The richest endpoint in the inspection system. Returns the full issue with **nested vehicle info**, **nested driver info**, and the **full linked inspection with all result item names**. Use this when the fleet manager taps into a specific issue.

```
GET /api/v1/vehicle-issues/{id}/
```

**Permission:** Any authenticated user

**Response `200 OK`**

```json
{
  "id": 15,
  "title": "Brake squealing — needs immediate check",
  "description": "Loud squealing noise on heavy braking. Could indicate worn brake pads.",
  "severity": "high",
  "status": "reported",
  "photo_url": "",
  "reported_at": "2026-03-17T08:33:00Z",
  "updated_at": "2026-03-17T08:33:00Z",

  "vehicle": {
    "id": 12,
    "registration_no": "MH-01-AB-1234",
    "make": "Tata",
    "model": "Prima",
    "year": 2022,
    "vin": "1HGBH41JXMN109186",
    "fuel_type": "diesel",
    "capacity_kg": "5000.00",
    "status": "available",
    "current_mileage_km": "45320.00",
    "last_service_date": "2026-01-10",
    "next_service_due_km": "50000.00",
    "next_service_due_date": "2026-06-10",
    "created_at": "2025-10-01T12:00:00Z",
    "updated_at": "2026-03-17T08:35:00Z"
  },

  "reported_by": {
    "id": 3,
    "username": "driver_rahul",
    "first_name": "Rahul",
    "last_name": "Sharma",
    "email": "rahul@example.com",
    "profile": {
      "role": "driver",
      "phone": "+91-9876543210",
      "profile_photo": null,
      "is_active": true,
      "first_time_login": false,
      "driver_status": "available",
      "created_at": "2025-10-01T12:00:00Z",
      "updated_at": "2026-03-17T08:35:00Z"
    }
  },

  "inspection": {
    "id": 47,
    "trip": null,
    "vehicle": 12,
    "driver": 3,
    "checklist": 1,
    "inspection_type": "pre_trip",
    "overall_status": "flagged",
    "notes": "Optional overall note.",
    "reviewed_by": null,
    "reviewed_at": null,
    "submitted_at": "2026-03-17T08:30:00Z",
    "created_at": "2026-03-17T08:30:00Z",
    "results": [
      {
        "id": 201,
        "checklist_item": 1,
        "checklist_item_name": "Tire Condition & Pressure",
        "result": "pass",
        "notes": "",
        "photo_url": ""
      },
      {
        "id": 202,
        "checklist_item": 2,
        "checklist_item_name": "Brake Condition & Response",
        "result": "fail",
        "notes": "Squealing noise on heavy braking.",
        "photo_url": "https://storage.example.com/photos/brake-photo.jpg"
      },
      {
        "id": 203,
        "checklist_item": 3,
        "checklist_item_name": "Lights & Blinkers",
        "result": "pass",
        "notes": "",
        "photo_url": ""
      },
      {
        "id": 204,
        "checklist_item": 4,
        "checklist_item_name": "Fuel Level",
        "result": "pass",
        "notes": "",
        "photo_url": ""
      },
      {
        "id": 205,
        "checklist_item": 5,
        "checklist_item_name": "Engine Condition",
        "result": "pass",
        "notes": "",
        "photo_url": ""
      }
    ]
  }
}
```

**Key things to render on the issue detail screen:**
- Vehicle registration, make/model
- Driver name and phone number (`reported_by.profile.phone`)
- Inspection submission time (`inspection.submitted_at`)
- All results — highlight `result === "fail"` rows in red, `"pass"` in green, `"na"` in grey
- The `checklist_item_name` field means you never need to look up item names separately

---

### 5.4 Update Issue Status *(Fleet Manager / Maintenance)*

```
PATCH /api/v1/vehicle-issues/{id}/
```

**Permission:** Any authenticated user (typically called by fleet_manager or maintenance_staff)

**Request Body** — send only the fields you want to update:

```json
{ "status": "acknowledged" }
```

You can also update other writable fields in the same call:

```json
{
  "status": "in_repair",
  "description": "Brake pads confirmed worn. Replacement scheduled for tomorrow."
}
```

**Writable fields via PATCH**

| Field | Type | Notes |
|-------|------|-------|
| `status` | string | `"reported"` → `"acknowledged"` → `"in_repair"` → `"resolved"` |
| `title` | string | |
| `description` | string | |
| `severity` | string | |
| `photo_url` | string (URL) | |

**Response `200 OK`** — Returns the updated issue (lightweight, same shape as list).

**Typical status lifecycle:**

```
reported  ──►  acknowledged  ──►  in_repair  ──►  resolved
  (driver)      (fleet mgr)       (fleet mgr)     (fleet mgr)
```

---

### 5.5 All Issues for a Vehicle

```
GET /api/v1/vehicles/{vehicle_id}/issues/
```

**Permission:** Any authenticated user

Returns a paginated list of all issues for the vehicle, ordered by `-reported_at`. Response shape is the same as [5.2 List Issues](#52-list-issues) (lightweight, IDs only for relations).

---

## 6. Full Schemas

### Inspection Object (full)

```
{
  id                integer     — unique ID
  trip              integer|null — linked trip ID (null until trip-start is called)
  vehicle           integer     — vehicle ID
  driver            integer     — driver user ID (auto-set from token on create)
  checklist         integer|null — checklist template ID
  inspection_type   string      — "pre_trip" | "post_trip" | "ad_hoc"
  overall_status    string      — "pending" | "approved" | "flagged"
  notes             string      — general notes
  reviewed_by       integer|null — user ID of reviewer (null until reviewed)
  reviewed_at       datetime|null
  submitted_at      datetime    — read-only, set on create
  created_at        datetime    — read-only
  results[]         array       — nested InspectionResult objects
}
```

### InspectionResult Object

```
{
  id              integer
  inspection      integer     — parent inspection ID
  checklist_item  integer     — item ID
  result          string      — "pass" | "fail" | "na"
  notes           string
  photo_url       string (URL)
}
```

### InspectionResult (detail view only — inside VehicleIssue detail)

```
{
  id                    integer
  checklist_item        integer     — item ID
  checklist_item_name   string      — item name (e.g. "Brake Condition & Response")
  result                string
  notes                 string
  photo_url             string
}
```

### VehicleIssue Object (list/create response)

```
{
  id           integer
  vehicle      integer     — vehicle ID
  reported_by  integer     — driver user ID (auto-set from token)
  inspection   integer|null — linked inspection ID
  title        string
  description  string
  severity     string      — "low" | "medium" | "high" | "critical"
  status       string      — "reported" | "acknowledged" | "in_repair" | "resolved"
  photo_url    string
  reported_at  datetime    — read-only
  updated_at   datetime    — read-only
}
```

### VehicleIssue Object (detail response — GET /vehicle-issues/:id/)

Same as above but `vehicle`, `reported_by`, and `inspection` are **fully nested objects** instead of IDs.

---

## 7. Enum Reference

### `inspection_type`
| Value | When to use |
|-------|-------------|
| `pre_trip` | Before trip starts (this driver flow) |
| `post_trip` | After trip completes |
| `ad_hoc` | Unscheduled, standalone inspection |

### `overall_status`
| Value | Set by | Meaning |
|-------|--------|---------|
| `pending` | Default (legacy) | Not yet evaluated |
| `approved` | Auto on create | All items passed |
| `flagged` | Auto on create | One or more items failed |

> Fleet managers can override `overall_status` via the `review` endpoint.

### `result` (per inspection item)
| Value | Meaning |
|-------|---------|
| `pass` | Item checked — OK |
| `fail` | Item checked — problem found |
| `na` | Not applicable |

### Issue `severity`
| Value | Colour suggestion | Meaning |
|-------|------------------|---------|
| `low` | Yellow | Minor, monitor |
| `medium` | Orange | Needs attention |
| `high` | Red | Significant concern |
| `critical` | Dark red / pulsing | Do not depart |

### Issue `status`
| Value | Set by | Meaning |
|-------|--------|---------|
| `reported` | Auto on create | Newly raised |
| `acknowledged` | Fleet manager | Seen and noted |
| `in_repair` | Fleet manager | Being fixed |
| `resolved` | Fleet manager | Fixed and closed |

---

## 8. Error Reference

| Status | Cause | Body |
|--------|-------|------|
| `400` | Missing required field | `{ "field_name": ["This field is required."] }` |
| `400` | Invalid enum value (e.g. bad `result`) | `{ "result": ["\"xyz\" is not a valid choice."] }` |
| `400` | Invalid URL in `photo_url` | `{ "photo_url": ["Enter a valid URL."] }` |
| `400` | `review` called with invalid status | `{ "detail": "status must be approved or flagged." }` |
| `400` | Starting a trip not in `assigned` status | `{ "detail": "Trip can only be started from assigned status." }` |
| `401` | Missing or expired JWT | `{ "detail": "Authentication credentials were not provided." }` |
| `403` | Driver calls fleet-manager-only endpoint | `{ "detail": "You do not have permission to perform this action." }` |
| `404` | Invalid ID in URL | `{ "detail": "Not found." }` |
| `404` | No active pre-trip checklist seeded | `{ "detail": "No active pre-trip checklist found." }` |

---

## 9. Complete Flow Walkthrough

### Driver — Pre-Trip Inspection

```
Screen: "Pre-Trip Inspection"

1. App loads  ──►  GET /inspection-checklists/pre_trip_default/
                   Store: checklist.id, items[].id + item_name

2. Driver taps pass/fail on each of the 5 items.
   Store locally: { checklist_item_id, result, notes, photo_url } per item.

3. Driver taps "Submit Inspection"

   ──►  POST /inspections/
        {
          vehicle: <vehicle_id>,
          checklist: <checklist.id>,
          inspection_type: "pre_trip",
          results: [ ...5 items... ]
        }

   ◄──  { id: 47, overall_status: "approved" | "flagged", results: [...] }
        Store inspection_id = 47


   ┌─────────────────────────┐     ┌──────────────────────────────────────┐
   │ overall_status ==        │     │ overall_status == "flagged"          │
   │ "approved"               │     │                                      │
   │                          │     │ • Show which items failed (in red)   │
   │ • Enable "Start Trip"    │     │ • Enable "Notify Fleet Manager" btn  │
   │ • Disable "Notify" btn   │     │ • Disable "Start Trip" btn           │
   └──────────┬───────────────┘     └──────────────┬───────────────────────┘
              │                                    │
              ▼                                    ▼

4a. Driver taps "Start Trip"          4b. Driver taps "Notify Fleet Manager"

    ──►  POST /trips/{trip_id}/start/      ──►  POST /vehicle-issues/
         {                                       {
           latitude: ...,                          vehicle: <vehicle_id>,
           longitude: ...,                         inspection: 47,
           start_mileage_km: ...,                  title: "...",
           inspection_id: 47                       description: "...",
         }                                         severity: "high"
                                                 }
    ◄──  Trip with status "in_progress"
         Inspection.trip = this trip        ◄──  { id: 15, status: "reported" }
                                                 Disable "Notify" button
                                                 Show confirmation message
```

---

### Fleet Manager — Reviewing an Issue

```
Screen: "Issues" (list view)

1.  GET /vehicle-issues/?status=reported&ordering=-reported_at
    Renders a card per issue: vehicle reg, driver name, severity badge, title.

2.  Fleet manager taps an issue card.

    ──►  GET /vehicle-issues/{id}/
    ◄──  Full nested response:
         - vehicle.registration_no, vehicle.make, vehicle.model
         - reported_by.first_name + last_name + profile.phone
         - inspection.submitted_at
         - inspection.results[]  ← render all 5 items
           - result == "fail"  → red row
           - result == "pass"  → green row
           - result == "na"    → grey row

3.  Fleet manager taps "Acknowledge"

    ──►  PATCH /vehicle-issues/{id}/
         { "status": "acknowledged" }

4.  Fleet manager assigns to maintenance team and taps "Mark In Repair"

    ──►  PATCH /vehicle-issues/{id}/
         { "status": "in_repair" }

5.  Issue is fixed. Fleet manager taps "Mark Resolved"

    ──►  PATCH /vehicle-issues/{id}/
         { "status": "resolved" }

6.  Optionally formally review the underlying inspection:

    ──►  POST /inspections/{inspection_id}/review/
         { "overall_status": "flagged" }
```

---

### All Inspection Endpoints at a Glance

| Method | Endpoint | Who | Purpose |
|--------|----------|-----|---------|
| `GET` | `/inspection-checklists/pre_trip_default/` | Driver | Get default checklist + item IDs |
| `GET` | `/inspection-checklists/` | Fleet Mgr / Maintenance | List all checklists |
| `GET` | `/inspection-checklists/{id}/` | Fleet Mgr / Maintenance | Get single checklist |
| `POST` | `/inspections/` | Driver | Submit inspection + all results |
| `GET` | `/inspections/` | All | List inspections (filterable) |
| `GET` | `/inspections/{id}/` | All | Get single inspection |
| `POST` | `/inspections/{id}/review/` | Fleet Mgr / Maintenance | Approve or flag inspection |
| `GET` | `/vehicles/{id}/inspections/` | All | All inspections for a vehicle |
| `POST` | `/vehicle-issues/` | Driver | Raise an issue |
| `GET` | `/vehicle-issues/` | All | List issues (filterable) |
| `GET` | `/vehicle-issues/{id}/` | All | Full nested issue detail |
| `PATCH` | `/vehicle-issues/{id}/` | Fleet Mgr / Maintenance | Update issue status |
| `GET` | `/vehicles/{id}/issues/` | All | All issues for a vehicle |

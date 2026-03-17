# Pre-Inspection Flow — Client Developer Guide

This document covers everything the client (mobile/web) needs to implement the driver pre-trip inspection flow and the fleet manager issue view. All requests require a valid JWT token in the `Authorization` header unless noted otherwise.

```
Authorization: Bearer <access_token>
```

Base URL: `https://<your-domain>/api/v1`

---

## Table of Contents

1. [Overview](#1-overview)
2. [Driver Flow](#2-driver-flow)
   - [Step 1 — Fetch the Pre-Trip Checklist](#step-1--fetch-the-pre-trip-checklist)
   - [Step 2 — Submit Inspection Results](#step-2--submit-inspection-results)
   - [Step 3a — Start the Trip (all passed)](#step-3a--start-the-trip-all-passed)
   - [Step 3b — Report an Issue (any failed)](#step-3b--report-an-issue-any-failed)
3. [Fleet Manager Flow](#3-fleet-manager-flow)
   - [List Issues](#list-issues)
   - [Get Full Issue Detail](#get-full-issue-detail)
   - [Update Issue Status](#update-issue-status)
   - [Review an Inspection](#review-an-inspection)
4. [Full Response Schemas](#4-full-response-schemas)
5. [Error Reference](#5-error-reference)
6. [End-to-End Flow Diagram](#6-end-to-end-flow-diagram)

---

## 1. Overview

Before a driver can start a trip, they must complete a pre-trip vehicle inspection covering 5 items. The result of that inspection determines what happens next:

| All 5 items pass | Any item fails |
|-----------------|----------------|
| `overall_status: "approved"` | `overall_status: "flagged"` |
| "Start Trip" button enabled | "Start Trip" button disabled |
| Call start-trip API with `inspection_id` | Show "Notify Fleet Manager" button |
| Trip begins | Driver calls report-issue API |

The backend auto-calculates `overall_status` — you do not need to send it.

---

## 2. Driver Flow

### Step 1 — Fetch the Pre-Trip Checklist

Fetch the active checklist to get the item names and their IDs. **Do this once when the inspection screen loads.** The IDs are needed when submitting results in Step 2.

```
GET /api/v1/inspection-checklists/pre_trip_default/
```

**Headers**
```
Authorization: Bearer <driver_token>
```

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

> **Note:** `items` is always ordered by `sequence_no`. Display them in this order.

---

### Step 2 — Submit Inspection Results

Once the driver has checked all items, submit the inspection in a single call. Each item gets a `result` of `"pass"`, `"fail"`, or `"na"`.

```
POST /api/v1/inspections/
```

**Headers**
```
Authorization: Bearer <driver_token>
Content-Type: application/json
```

**Request Body**
```json
{
  "vehicle": 12,
  "checklist": 1,
  "inspection_type": "pre_trip",
  "notes": "Front-left tire looks low.",
  "results": [
    { "checklist_item_id": 1, "result": "fail", "notes": "Low pressure on front-left", "photo_url": "" },
    { "checklist_item_id": 2, "result": "pass" },
    { "checklist_item_id": 3, "result": "pass" },
    { "checklist_item_id": 4, "result": "pass" },
    { "checklist_item_id": 5, "result": "pass" }
  ]
}
```

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `vehicle` | integer | Yes | ID of the vehicle being inspected |
| `checklist` | integer | Yes | Use the `id` from Step 1 |
| `inspection_type` | string | Yes | Always `"pre_trip"` for this flow |
| `notes` | string | No | Overall notes for the inspection |
| `results` | array | Yes | One entry per checklist item |
| `results[].checklist_item_id` | integer | Yes | The `id` from `items[]` in Step 1 |
| `results[].result` | string | Yes | `"pass"`, `"fail"`, or `"na"` |
| `results[].notes` | string | No | Notes specific to this item |
| `results[].photo_url` | string (URL) | No | Photo evidence for this item |

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
  "notes": "Front-left tire looks low.",
  "reviewed_by": null,
  "reviewed_at": null,
  "submitted_at": "2026-03-17T08:30:00Z",
  "created_at": "2026-03-17T08:30:00Z",
  "results": [
    { "id": 201, "inspection": 47, "checklist_item": 1, "result": "fail",  "notes": "Low pressure on front-left", "photo_url": "" },
    { "id": 202, "inspection": 47, "checklist_item": 2, "result": "pass",  "notes": "", "photo_url": "" },
    { "id": 203, "inspection": 47, "checklist_item": 3, "result": "pass",  "notes": "", "photo_url": "" },
    { "id": 204, "inspection": 47, "checklist_item": 4, "result": "pass",  "notes": "", "photo_url": "" },
    { "id": 205, "inspection": 47, "checklist_item": 5, "result": "pass",  "notes": "", "photo_url": "" }
  ]
}
```

**`overall_status` logic (set by the backend automatically):**

| Condition | `overall_status` |
|-----------|-----------------|
| All results are `"pass"` or `"na"` | `"approved"` |
| At least one result is `"fail"` | `"flagged"` |

> **Save `id` (the inspection ID)** — you will need it in Step 3a or 3b.

---

### Step 3a — Start the Trip (all passed)

Only call this when `overall_status === "approved"`. Pass the `inspection_id` so the backend links the inspection to the trip.

```
POST /api/v1/trips/{trip_id}/start/
```

**Headers**
```
Authorization: Bearer <driver_token>
Content-Type: application/json
```

**Request Body**
```json
{
  "latitude": 6.5244,
  "longitude": 3.3792,
  "start_mileage_km": 45320,
  "inspection_id": 47
}
```

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `latitude` | number | No | Driver's current GPS latitude |
| `longitude` | number | No | Driver's current GPS longitude |
| `start_mileage_km` | number | No | Current odometer reading |
| `inspection_id` | integer | No | ID from Step 2. Links the inspection to this trip. |

> `inspection_id` is optional — the trip starts regardless. But always send it so the fleet manager can trace inspections to trips.

**Response `200 OK`** — Full trip object with `status: "in_progress"`.

```json
{
  "id": 88,
  "status": "in_progress",
  "started_at": "2026-03-17T08:35:00Z",
  "vehicle": 12,
  "driver": 3,
  ...
}
```

**What happens on the backend:**
- `Trip.status` → `"in_progress"`
- `Vehicle.status` → `"in_trip"`
- `Order.status` → `"in_transit"`
- `UserProfile.driver_status` → `"in_trip"`
- `Inspection.trip` → linked to this trip

---

### Step 3b — Report an Issue (any failed)

Call this when `overall_status === "flagged"` and the driver taps "Notify Fleet Manager". Always include the `inspection` ID so the fleet manager can see the full context.

```
POST /api/v1/vehicle-issues/
```

**Headers**
```
Authorization: Bearer <driver_token>
Content-Type: application/json
```

**Request Body**
```json
{
  "vehicle": 12,
  "inspection": 47,
  "title": "Tire pressure issue — front-left",
  "description": "Front-left tire has visibly low pressure. Needs inspection before departure.",
  "severity": "high"
}
```

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `vehicle` | integer | Yes | ID of the vehicle |
| `inspection` | integer | No | ID from Step 2 — strongly recommended |
| `title` | string | Yes | Short summary (max 255 chars) |
| `description` | string | No | Detailed description |
| `severity` | string | Yes | `"low"`, `"medium"`, `"high"`, or `"critical"` |
| `photo_url` | string (URL) | No | Optional photo evidence |

**Severity guide:**

| Value | When to use |
|-------|-------------|
| `"low"` | Minor cosmetic issue, can be monitored |
| `"medium"` | Needs attention but trip may still proceed with approval |
| `"high"` | Significant safety or operational concern |
| `"critical"` | Vehicle must not depart — immediate repair needed |

**Response `201 Created`**
```json
{
  "id": 15,
  "vehicle": 12,
  "reported_by": 3,
  "inspection": 47,
  "title": "Tire pressure issue — front-left",
  "description": "Front-left tire has visibly low pressure...",
  "severity": "high",
  "status": "reported",
  "photo_url": "",
  "reported_at": "2026-03-17T08:33:00Z",
  "updated_at": "2026-03-17T08:33:00Z"
}
```

**What happens on the backend:**
- Issue is saved with `status: "reported"`
- All **fleet managers** and **maintenance staff** receive an in-app notification (`alert_type: "issue_reported"`) instantly via WebSocket
- The notification's `reference_id` is the issue ID

> After successfully creating the issue, show the driver a confirmation and disable the "Notify Fleet Manager" button to prevent duplicate reports.

---

## 3. Fleet Manager Flow

### List Issues

```
GET /api/v1/vehicle-issues/
```

Supports the following query parameters for filtering:

| Param | Example | Description |
|-------|---------|-------------|
| `vehicle` | `?vehicle=12` | Filter by vehicle ID |
| `severity` | `?severity=high` | Filter by severity |
| `status` | `?status=reported` | Filter by issue status |
| `reported_by` | `?reported_by=3` | Filter by driver ID |
| `search` | `?search=tire` | Search title and description |
| `ordering` | `?ordering=-reported_at` | Sort (prefix `-` for descending) |

**Response `200 OK`** — Paginated list (lightweight, IDs only for relations):
```json
{
  "count": 3,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": 15,
      "vehicle": 12,
      "reported_by": 3,
      "inspection": 47,
      "title": "Tire pressure issue — front-left",
      "severity": "high",
      "status": "reported",
      "reported_at": "2026-03-17T08:33:00Z"
    },
    ...
  ]
}
```

---

### Get Full Issue Detail

This is the rich endpoint — use it when the fleet manager taps into a specific issue. It returns fully nested vehicle info, driver info, and the complete inspection with every check result and item name.

```
GET /api/v1/vehicle-issues/{id}/
```

**Response `200 OK`**
```json
{
  "id": 15,
  "title": "Tire pressure issue — front-left",
  "description": "Front-left tire has visibly low pressure. Needs inspection before departure.",
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
    "status": "available",
    "current_mileage_km": "45320.00"
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
      "driver_status": "available"
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
    "notes": "Front-left tire looks low.",
    "reviewed_by": null,
    "reviewed_at": null,
    "submitted_at": "2026-03-17T08:30:00Z",
    "results": [
      { "id": 201, "checklist_item": 1, "checklist_item_name": "Tire Condition & Pressure",  "result": "fail", "notes": "Low pressure on front-left", "photo_url": "" },
      { "id": 202, "checklist_item": 2, "checklist_item_name": "Brake Condition & Response", "result": "pass", "notes": "", "photo_url": "" },
      { "id": 203, "checklist_item": 3, "checklist_item_name": "Lights & Blinkers",          "result": "pass", "notes": "", "photo_url": "" },
      { "id": 204, "checklist_item": 4, "checklist_item_name": "Fuel Level",                 "result": "pass", "notes": "", "photo_url": "" },
      { "id": 205, "checklist_item": 5, "checklist_item_name": "Engine Condition",           "result": "pass", "notes": "", "photo_url": "" }
    ]
  }
}
```

> Results include both passed and failed items. Use `result === "fail"` to highlight failed items in red.

---

### Update Issue Status

As the fleet manager acts on the issue, update its status accordingly.

```
PATCH /api/v1/vehicle-issues/{id}/
```

**Request Body**
```json
{ "status": "acknowledged" }
```

| `status` value | Meaning |
|----------------|---------|
| `"reported"` | Newly raised, awaiting review |
| `"acknowledged"` | Fleet manager has seen it |
| `"in_repair"` | Maintenance team is working on it |
| `"resolved"` | Issue has been fixed |

**Response `200 OK`** — Returns the updated issue (lightweight, same as list).

---

### Review an Inspection

Optionally, the fleet manager can formally approve or flag an inspection after reviewing it.

```
POST /api/v1/inspections/{inspection_id}/review/
```

**Request Body**
```json
{ "overall_status": "approved" }
```

Accepted values: `"approved"` or `"flagged"`.

**Response `200 OK`** — Returns the full inspection with `reviewed_by` and `reviewed_at` set.

---

## 4. Full Response Schemas

### `overall_status` values

| Value | Set by | Meaning |
|-------|--------|---------|
| `"pending"` | — | Should not appear after Step 2 (legacy) |
| `"approved"` | Auto on create | All items passed |
| `"flagged"` | Auto on create | One or more items failed |

### `inspection_type` values

| Value | Used for |
|-------|----------|
| `"pre_trip"` | Pre-departure inspection (this flow) |
| `"post_trip"` | Post-arrival inspection |
| `"ad_hoc"` | Unscheduled inspection |

### `result` values (per inspection item)

| Value | Meaning |
|-------|---------|
| `"pass"` | Item checked and OK |
| `"fail"` | Item checked and has a problem |
| `"na"` | Not applicable for this vehicle/trip |

### Issue `severity` values

| Value | Meaning |
|-------|---------|
| `"low"` | Minor issue |
| `"medium"` | Moderate issue |
| `"high"` | Significant safety/operational concern |
| `"critical"` | Vehicle must not depart |

### Issue `status` values

| Value | Set by |
|-------|--------|
| `"reported"` | Auto on creation |
| `"acknowledged"` | Fleet manager |
| `"in_repair"` | Fleet manager / maintenance staff |
| `"resolved"` | Fleet manager / maintenance staff |

---

## 5. Error Reference

| HTTP Status | When it happens | Response body |
|-------------|-----------------|---------------|
| `400 Bad Request` | Missing required fields, invalid `result` value, invalid `severity` | `{ "field_name": ["error message"] }` |
| `401 Unauthorized` | Missing or expired JWT token | `{ "detail": "Authentication credentials were not provided." }` |
| `403 Forbidden` | Driver calls a fleet-manager-only endpoint | `{ "detail": "You do not have permission to perform this action." }` |
| `404 Not Found` | Invalid trip/vehicle/issue ID, or no active pre-trip checklist seeded | `{ "detail": "Not found." }` or `{ "detail": "No active pre-trip checklist found." }` |
| `400 Bad Request` | Trying to start a trip that is not in `"assigned"` status | `{ "detail": "Trip can only be started from assigned status." }` |

---

## 6. End-to-End Flow Diagram

```
DRIVER APP                              BACKEND
─────────────────────────────────────────────────────────────────

[Inspection Screen Opens]
        │
        ├──► GET /inspection-checklists/pre_trip_default/ ──────► Returns 5 items with IDs
        │
[Driver checks each item: pass / fail]
        │
        ├──► POST /inspections/ ─────────────────────────────────► Saves Inspection + Results
        │        { vehicle, checklist, inspection_type,            Auto-sets overall_status:
        │          results: [{id, result}, ...] }                    "approved" or "flagged"
        │
        │◄── Response: { id: 47, overall_status: "..." }
        │
    ┌───┴────────────────────────────────┐
    │ overall_status == "approved"?      │ overall_status == "flagged"?
    │                                    │
    ▼                                    ▼
[Enable "Start Trip"]             [Disable "Start Trip"]
        │                         [Show "Notify Fleet Manager"]
        │                                    │
        ▼                                    ▼
POST /trips/{id}/start/          POST /vehicle-issues/
  { inspection_id: 47, ... }       { vehicle, inspection: 47,
                                     title, severity }
        │                                    │
        ▼                                    ▼
  Trip starts,                   Issue created (status: "reported")
  Inspection linked to trip      Fleet managers + maintenance staff
                                 notified via WebSocket + DB notification


─────────────────────────────────────────────────────────────────
FLEET MANAGER APP

[Receives push notification: "New issue: Tire pressure issue"]
        │
        ├──► GET /vehicle-issues/?status=reported    (list view)
        │
        ├──► GET /vehicle-issues/15/                 (tap into issue)
        │         Returns: vehicle info + driver info +
        │                  full inspection with all 5 results
        │
        ├──► PATCH /vehicle-issues/15/               (update status)
        │         { "status": "acknowledged" }
        │
        └──► POST /inspections/47/review/            (optional formal review)
                  { "overall_status": "flagged" }
```

---

## Quick Reference — API Endpoints

| Method | Endpoint | Who calls it | Purpose |
|--------|----------|--------------|---------|
| `GET` | `/inspection-checklists/pre_trip_default/` | Driver | Get checklist + item IDs |
| `POST` | `/inspections/` | Driver | Submit inspection results |
| `POST` | `/trips/{id}/start/` | Driver | Start trip, link inspection |
| `POST` | `/vehicle-issues/` | Driver | Report issue to fleet manager |
| `GET` | `/vehicle-issues/` | Fleet Manager | List all issues (filterable) |
| `GET` | `/vehicle-issues/{id}/` | Fleet Manager | Full issue detail (nested) |
| `PATCH` | `/vehicle-issues/{id}/` | Fleet Manager | Update issue status |
| `POST` | `/inspections/{id}/review/` | Fleet Manager | Formally approve/flag inspection |

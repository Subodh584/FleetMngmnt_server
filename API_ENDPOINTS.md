# Fleet Management Server — API Endpoints

**Base URL:** `http://localhost:8000/api/v1/`

---

## Table of Contents

- [Authentication](#authentication)
- [Core](#core)
- [Fleet](#fleet)
- [Trips](#trips)
- [Maintenance](#maintenance)
- [Communications](#communications)
- [WebSocket Endpoints](#websocket-endpoints)
- [Documentation](#documentation)

---

## Authentication

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/auth/register/` | Register a new user |
| `POST` | `/api/v1/auth/token/` | Obtain JWT access + refresh tokens |
| `POST` | `/api/v1/auth/token/refresh/` | Refresh an expired access token |
| `GET` / `PUT` / `PATCH` | `/api/v1/auth/me/` | Get or update current user profile |
| `POST` | `/api/v1/auth/change-password/` | Change current user password |

---

## Core

### Users (read-only)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/users/` | List all users |
| `GET` | `/api/v1/users/{id}/` | Retrieve a user |

### Locations

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/locations/` | List all locations |
| `POST` | `/api/v1/locations/` | Create a location |
| `GET` | `/api/v1/locations/{id}/` | Retrieve a location |
| `PUT` | `/api/v1/locations/{id}/` | Update a location |
| `PATCH` | `/api/v1/locations/{id}/` | Partial update a location |
| `DELETE` | `/api/v1/locations/{id}/` | Delete a location |

### Geofences

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/geofences/` | List all geofences |
| `POST` | `/api/v1/geofences/` | Create a geofence |
| `GET` | `/api/v1/geofences/{id}/` | Retrieve a geofence |
| `PUT` | `/api/v1/geofences/{id}/` | Update a geofence |
| `PATCH` | `/api/v1/geofences/{id}/` | Partial update a geofence |
| `DELETE` | `/api/v1/geofences/{id}/` | Delete a geofence |

---

## Fleet

### Vehicles

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/fleet/vehicles/` | List all vehicles |
| `POST` | `/api/v1/fleet/vehicles/` | Create a vehicle |
| `GET` | `/api/v1/fleet/vehicles/{id}/` | Retrieve a vehicle |
| `PUT` | `/api/v1/fleet/vehicles/{id}/` | Update a vehicle |
| `PATCH` | `/api/v1/fleet/vehicles/{id}/` | Partial update a vehicle |
| `DELETE` | `/api/v1/fleet/vehicles/{id}/` | Delete a vehicle |
| `GET` | `/api/v1/fleet/vehicles/{id}/inspections/` | List inspections for a vehicle |
| `GET` | `/api/v1/fleet/vehicles/{id}/issues/` | List issues for a vehicle |

### Inspection Checklists

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/fleet/inspection-checklists/` | List all inspection checklists |
| `POST` | `/api/v1/fleet/inspection-checklists/` | Create an inspection checklist |
| `GET` | `/api/v1/fleet/inspection-checklists/{id}/` | Retrieve an inspection checklist |
| `PUT` | `/api/v1/fleet/inspection-checklists/{id}/` | Update an inspection checklist |
| `PATCH` | `/api/v1/fleet/inspection-checklists/{id}/` | Partial update an inspection checklist |
| `DELETE` | `/api/v1/fleet/inspection-checklists/{id}/` | Delete an inspection checklist |

### Inspection Checklist Items

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/fleet/inspection-checklist-items/` | List all checklist items |
| `POST` | `/api/v1/fleet/inspection-checklist-items/` | Create a checklist item |
| `GET` | `/api/v1/fleet/inspection-checklist-items/{id}/` | Retrieve a checklist item |
| `PUT` | `/api/v1/fleet/inspection-checklist-items/{id}/` | Update a checklist item |
| `PATCH` | `/api/v1/fleet/inspection-checklist-items/{id}/` | Partial update a checklist item |
| `DELETE` | `/api/v1/fleet/inspection-checklist-items/{id}/` | Delete a checklist item |

### Inspections

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/fleet/inspections/` | List all inspections |
| `POST` | `/api/v1/fleet/inspections/` | Create an inspection (with nested results) |
| `GET` | `/api/v1/fleet/inspections/{id}/` | Retrieve an inspection |
| `PUT` | `/api/v1/fleet/inspections/{id}/` | Update an inspection |
| `PATCH` | `/api/v1/fleet/inspections/{id}/` | Partial update an inspection |
| `DELETE` | `/api/v1/fleet/inspections/{id}/` | Delete an inspection |
| `POST` | `/api/v1/fleet/inspections/{id}/review/` | Review/approve an inspection |

### Vehicle Issues

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/fleet/vehicle-issues/` | List all vehicle issues |
| `POST` | `/api/v1/fleet/vehicle-issues/` | Report a vehicle issue |
| `GET` | `/api/v1/fleet/vehicle-issues/{id}/` | Retrieve a vehicle issue |
| `PUT` | `/api/v1/fleet/vehicle-issues/{id}/` | Update a vehicle issue |
| `PATCH` | `/api/v1/fleet/vehicle-issues/{id}/` | Partial update a vehicle issue |
| `DELETE` | `/api/v1/fleet/vehicle-issues/{id}/` | Delete a vehicle issue |

---

## Trips

### Orders

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/trips/orders/` | List all orders |
| `POST` | `/api/v1/trips/orders/` | Create an order (with nested drop points) |
| `GET` | `/api/v1/trips/orders/{id}/` | Retrieve an order |
| `PUT` | `/api/v1/trips/orders/{id}/` | Update an order |
| `PATCH` | `/api/v1/trips/orders/{id}/` | Partial update an order |
| `DELETE` | `/api/v1/trips/orders/{id}/` | Delete an order |

### Order Drop Points

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/trips/order-drop-points/` | List all order drop points |
| `POST` | `/api/v1/trips/order-drop-points/` | Create a drop point |
| `GET` | `/api/v1/trips/order-drop-points/{id}/` | Retrieve a drop point |
| `PUT` | `/api/v1/trips/order-drop-points/{id}/` | Update a drop point |
| `PATCH` | `/api/v1/trips/order-drop-points/{id}/` | Partial update a drop point |
| `DELETE` | `/api/v1/trips/order-drop-points/{id}/` | Delete a drop point |

### Trips

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/trips/trips/` | List all trips |
| `POST` | `/api/v1/trips/trips/` | Create a trip |
| `GET` | `/api/v1/trips/trips/{id}/` | Retrieve a trip |
| `PUT` | `/api/v1/trips/trips/{id}/` | Update a trip |
| `PATCH` | `/api/v1/trips/trips/{id}/` | Partial update a trip |
| `DELETE` | `/api/v1/trips/trips/{id}/` | Delete a trip |
| `POST` | `/api/v1/trips/trips/{id}/start/` | Start a trip |
| `POST` | `/api/v1/trips/trips/{id}/complete/` | Complete a trip |
| `POST` | `/api/v1/trips/trips/{id}/cancel/` | Cancel a trip |
| `GET` | `/api/v1/trips/trips/{id}/tracking/` | Get latest GPS position for a trip |
| `GET` | `/api/v1/trips/trips/{id}/gps_history/` | Get full GPS history for a trip |
| `GET` | `/api/v1/trips/trips/{id}/expenses/` | List expenses for a trip |
| `GET` | `/api/v1/trips/trips/{id}/fuel/` | List fuel logs for a trip |

### Routes

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/trips/routes/` | List all routes |
| `POST` | `/api/v1/trips/routes/` | Create a route |
| `GET` | `/api/v1/trips/routes/{id}/` | Retrieve a route |
| `PUT` | `/api/v1/trips/routes/{id}/` | Update a route |
| `PATCH` | `/api/v1/trips/routes/{id}/` | Partial update a route |
| `DELETE` | `/api/v1/trips/routes/{id}/` | Delete a route |
| `POST` | `/api/v1/trips/routes/{id}/approve/` | Approve a route |

### Route Deviations

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/trips/route-deviations/` | List all route deviations |
| `POST` | `/api/v1/trips/route-deviations/` | Create a route deviation record |
| `GET` | `/api/v1/trips/route-deviations/{id}/` | Retrieve a route deviation |
| `PUT` | `/api/v1/trips/route-deviations/{id}/` | Update a route deviation |
| `PATCH` | `/api/v1/trips/route-deviations/{id}/` | Partial update a route deviation |
| `DELETE` | `/api/v1/trips/route-deviations/{id}/` | Delete a route deviation |

### GPS Logs

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/trips/gps-logs/` | List all GPS logs |
| `POST` | `/api/v1/trips/gps-logs/` | Create a GPS log entry |
| `GET` | `/api/v1/trips/gps-logs/{id}/` | Retrieve a GPS log |

### Geofence Events

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/trips/geofence-events/` | List all geofence events |
| `POST` | `/api/v1/trips/geofence-events/` | Create a geofence event |
| `GET` | `/api/v1/trips/geofence-events/{id}/` | Retrieve a geofence event |

### Trip Expenses

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/trips/trip-expenses/` | List all trip expenses |
| `POST` | `/api/v1/trips/trip-expenses/` | Create a trip expense |
| `GET` | `/api/v1/trips/trip-expenses/{id}/` | Retrieve a trip expense |
| `PUT` | `/api/v1/trips/trip-expenses/{id}/` | Update a trip expense |
| `PATCH` | `/api/v1/trips/trip-expenses/{id}/` | Partial update a trip expense |
| `DELETE` | `/api/v1/trips/trip-expenses/{id}/` | Delete a trip expense |

### Fuel Logs

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/trips/fuel-logs/` | List all fuel logs |
| `POST` | `/api/v1/trips/fuel-logs/` | Create a fuel log |
| `GET` | `/api/v1/trips/fuel-logs/{id}/` | Retrieve a fuel log |
| `PUT` | `/api/v1/trips/fuel-logs/{id}/` | Update a fuel log |
| `PATCH` | `/api/v1/trips/fuel-logs/{id}/` | Partial update a fuel log |
| `DELETE` | `/api/v1/trips/fuel-logs/{id}/` | Delete a fuel log |

### Delivery Proofs

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/trips/delivery-proofs/` | List all delivery proofs |
| `POST` | `/api/v1/trips/delivery-proofs/` | Upload a delivery proof |
| `GET` | `/api/v1/trips/delivery-proofs/{id}/` | Retrieve a delivery proof |
| `PUT` | `/api/v1/trips/delivery-proofs/{id}/` | Update a delivery proof |
| `PATCH` | `/api/v1/trips/delivery-proofs/{id}/` | Partial update a delivery proof |
| `DELETE` | `/api/v1/trips/delivery-proofs/{id}/` | Delete a delivery proof |
| `POST` | `/api/v1/trips/delivery-proofs/{id}/verify/` | Verify a delivery proof |

---

## Maintenance

### Maintenance Schedules

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/maintenance/maintenance-schedules/` | List all maintenance schedules |
| `POST` | `/api/v1/maintenance/maintenance-schedules/` | Create a maintenance schedule |
| `GET` | `/api/v1/maintenance/maintenance-schedules/{id}/` | Retrieve a maintenance schedule |
| `PUT` | `/api/v1/maintenance/maintenance-schedules/{id}/` | Update a maintenance schedule |
| `PATCH` | `/api/v1/maintenance/maintenance-schedules/{id}/` | Partial update a maintenance schedule |
| `DELETE` | `/api/v1/maintenance/maintenance-schedules/{id}/` | Delete a maintenance schedule |

### Maintenance Records

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/maintenance/maintenance-records/` | List all maintenance records |
| `POST` | `/api/v1/maintenance/maintenance-records/` | Create a maintenance record (with nested spare parts) |
| `GET` | `/api/v1/maintenance/maintenance-records/{id}/` | Retrieve a maintenance record |
| `PUT` | `/api/v1/maintenance/maintenance-records/{id}/` | Update a maintenance record |
| `PATCH` | `/api/v1/maintenance/maintenance-records/{id}/` | Partial update a maintenance record |
| `DELETE` | `/api/v1/maintenance/maintenance-records/{id}/` | Delete a maintenance record |
| `POST` | `/api/v1/maintenance/maintenance-records/{id}/start_repair/` | Start repair (sets vehicle to `in_maintenance`) |
| `POST` | `/api/v1/maintenance/maintenance-records/{id}/complete_repair/` | Complete repair (sets vehicle back to `active`) |

### Spare Parts Used

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/maintenance/spare-parts/` | List all spare parts used |
| `POST` | `/api/v1/maintenance/spare-parts/` | Record spare part usage |
| `GET` | `/api/v1/maintenance/spare-parts/{id}/` | Retrieve spare part record |
| `PUT` | `/api/v1/maintenance/spare-parts/{id}/` | Update spare part record |
| `PATCH` | `/api/v1/maintenance/spare-parts/{id}/` | Partial update spare part record |
| `DELETE` | `/api/v1/maintenance/spare-parts/{id}/` | Delete spare part record |

---

## Communications

### Messages

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/comms/messages/` | List all messages (filter by `?peer=<user_id>`) |
| `POST` | `/api/v1/comms/messages/` | Send a message |
| `GET` | `/api/v1/comms/messages/{id}/` | Retrieve a message |
| `POST` | `/api/v1/comms/messages/{id}/mark_read/` | Mark a single message as read |
| `POST` | `/api/v1/comms/messages/mark_all_read/` | Mark all messages from a peer as read |

### Notifications

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/comms/notifications/` | List all notifications for current user |
| `POST` | `/api/v1/comms/notifications/` | Create a notification |
| `GET` | `/api/v1/comms/notifications/{id}/` | Retrieve a notification |
| `POST` | `/api/v1/comms/notifications/{id}/mark_read/` | Mark a notification as read |
| `POST` | `/api/v1/comms/notifications/mark_all_read/` | Mark all notifications as read |
| `GET` | `/api/v1/comms/notifications/unread_count/` | Get count of unread notifications |

### SOS Alerts

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/comms/sos-alerts/` | List all SOS alerts |
| `POST` | `/api/v1/comms/sos-alerts/` | Create an SOS alert |
| `GET` | `/api/v1/comms/sos-alerts/{id}/` | Retrieve an SOS alert |
| `POST` | `/api/v1/comms/sos-alerts/{id}/resolve/` | Resolve an SOS alert |

---

## WebSocket Endpoints

> Connect via `ws://localhost:8000/<path>?token=<JWT_ACCESS_TOKEN>`

| Endpoint | Description |
|----------|-------------|
| `ws/trips/{trip_id}/gps/` | Real-time GPS tracking for a trip. Send `{"latitude": ..., "longitude": ..., "speed": ..., "heading": ...}` to log and broadcast GPS data. |
| `ws/notifications/` | Receive real-time push notifications. Supports `mark_read` action: `{"action": "mark_read", "notification_id": ...}` |
| `ws/chat/{peer_id}/` | Real-time chat with another user. Send `{"message": "...", "trip_id": ...}` (trip_id optional). |

---

## Documentation (Auto-Generated)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/docs/` | Swagger UI (interactive API docs) |
| `GET` | `/api/v1/redoc/` | ReDoc (alternative API docs) |
| `GET` | `/api/v1/schema/` | Download OpenAPI 3.0 schema (YAML) |

---

## Notes

- **Authentication:** All endpoints (except `register`, `token`, `token/refresh`, and docs) require a JWT Bearer token in the `Authorization` header:
  ```
  Authorization: Bearer <access_token>
  ```
- **Pagination:** All list endpoints return paginated results (25 items per page). Use `?page=2` to navigate.
- **Filtering:** Most list endpoints support filtering via query parameters (e.g., `?status=active`, `?vehicle=1`).
- **Search:** Endpoints with `search_fields` support `?search=<term>` for text search.
- **Ordering:** Use `?ordering=field_name` (prefix with `-` for descending, e.g., `?ordering=-created_at`).

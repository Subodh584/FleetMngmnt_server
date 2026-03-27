# Fleet Management AI Assistant — Developer Guide

The AI assistant lets any authenticated user ask natural-language questions about the fleet database. It uses **Mistral AI** (via LangChain) with **ConversationBufferWindowMemory** for full session context, and enforces **read-only access through 4 independent layers** — none of which rely on AI behaviour.

---

## Setup Checklist

Before the assistant works, make sure your `.env` has these two variables:

```env
MISTRAL_API_KEY=your_mistral_api_key_here
AI_ASSISTANT_DB_URL=postgresql://ai_readonly:your_password@db.YOUR_PROJECT.supabase.co:5432/postgres
```

> **Important:** Use port `5432` (direct connection), NOT `6543` (PgBouncer). LangChain's SQLAlchemy manages its own connection pool.

If either variable is missing the endpoint returns `HTTP 503` immediately — no agent is started.

---

## Authentication

All endpoints require a valid JWT Bearer token.

```
Authorization: Bearer <access_token>
```

Get a token from `POST /api/v1/auth/token/` with `username` + `password`.

---

## Rate Limiting

Each user is limited to **20 requests per hour** on the chat endpoint.
On exceeding the limit the server returns `HTTP 429 Too Many Requests`.

---

## Endpoints

### 1. Send a Message

```
POST /api/v1/ai/chat/
```

The main endpoint. Send a question, get a response from the AI.
The bot automatically remembers the last **5 exchanges (10 messages)** of the current session.

**Headers**
```
Authorization: Bearer <token>
Content-Type: application/json
```

**Request Body**

| Field | Type | Required | Description |
|---|---|---|---|
| `message` | string | Yes | Your question (max 1000 characters) |
| `session_id` | integer | No | ID of an existing session to continue. Omit to start a new conversation. |

**Example — Start a new conversation**
```json
{
    "message": "How many vehicles are currently available?"
}
```

**Example — Continue an existing conversation (follow-up)**
```json
{
    "message": "Which of those are diesel?",
    "session_id": 14
}
```

The bot resolves pronouns like *"those"*, *"them"*, *"the ones you mentioned"* using the stored session memory — no need to repeat context.

**Response — `200 OK`**

```json
{
    "session_id": 14,
    "session_title": "How many vehicles are currently avail...",
    "message": {
        "id": 28,
        "role": "ai",
        "content": "Hi Ahmed! There are currently 7 available vehicles...",
        "created_at": "2026-03-27T10:30:00.123456Z"
    },
    "suggested_questions": [
        "How many vehicles are currently available?",
        "Show me all trips in progress right now.",
        "Which vehicles are due for maintenance soon?",
        "Are there any unresolved SOS alerts?",
        "How many orders are pending assignment?"
    ]
}
```

> `suggested_questions` is only included on the **first message** of a new session. Use it to render starter prompts in your UI.

**Response — `400 Bad Request`** (validation error)
```json
{
    "message": ["This field is required."]
}
```

**Response — `404 Not Found`** (invalid session_id)
```json
{
    "error": "Session not found."
}
```

**Response — `429 Too Many Requests`** (rate limit exceeded)
```json
{
    "detail": "Request was throttled. Expected available in 3600 seconds."
}
```

**Response — `503 Service Unavailable`** (missing `.env` config)
```json
{
    "error": "AI assistant is not configured (missing MISTRAL_API_KEY)."
}
```

---

### 2. Get Messages in a Session

```
GET /api/v1/ai/chat/history/?session_id=<id>
```

Returns the full conversation history for one session — all human and AI messages in chronological order.

**Headers**
```
Authorization: Bearer <token>
```

**Query Parameters**

| Param | Type | Required | Description |
|---|---|---|---|
| `session_id` | integer | Yes | The session to retrieve |

**Example Request**
```
GET /api/v1/ai/chat/history/?session_id=14
```

**Response — `200 OK`**
```json
{
    "session_id": 14,
    "session_title": "How many vehicles are currently avail...",
    "messages": [
        {
            "id": 27,
            "role": "human",
            "content": "How many vehicles are currently available?",
            "created_at": "2026-03-27T10:29:55.000000Z"
        },
        {
            "id": 28,
            "role": "ai",
            "content": "Hi Ahmed! There are currently 7 available vehicles...",
            "created_at": "2026-03-27T10:30:00.123456Z"
        },
        {
            "id": 29,
            "role": "human",
            "content": "Which of those are diesel?",
            "created_at": "2026-03-27T10:30:45.000000Z"
        },
        {
            "id": 30,
            "role": "ai",
            "content": "Of the 7 available vehicles, 5 are diesel...",
            "created_at": "2026-03-27T10:30:51.654321Z"
        }
    ]
}
```

**Response — `400 Bad Request`** (missing session_id)
```json
{
    "error": "session_id query parameter is required."
}
```

**Response — `404 Not Found`**
```json
{
    "error": "Session not found."
}
```

---

### 3. List All Sessions

```
GET /api/v1/ai/chat/sessions/
```

Returns the 20 most recent chat sessions for the authenticated user, sorted by last activity. Use this to render a conversation history sidebar.

**Headers**
```
Authorization: Bearer <token>
```

**No query parameters.**

**Response — `200 OK`**
```json
{
    "sessions": [
        {
            "id": 14,
            "title": "How many vehicles are currently avail...",
            "created_at": "2026-03-27T10:29:55.000000Z",
            "updated_at": "2026-03-27T10:30:51.654321Z",
            "last_message": {
                "role": "ai",
                "content": "Of the 7 available vehicles, 5 are diesel..."
            },
            "message_count": 4
        },
        {
            "id": 11,
            "title": "Show me pending leave requests",
            "created_at": "2026-03-26T14:15:00.000000Z",
            "updated_at": "2026-03-26T14:15:42.000000Z",
            "last_message": {
                "role": "ai",
                "content": "Hi Ahmed! There are 3 pending leave requests..."
            },
            "message_count": 2
        }
    ]
}
```

---

### 4. Clear a Session

```
DELETE /api/v1/ai/chat/sessions/<session_id>/clear/
```

Deletes all messages inside a session and resets its title to "New Chat". The session itself is kept so you can reuse the `session_id`.

**Headers**
```
Authorization: Bearer <token>
```

**URL Parameter**

| Param | Type | Description |
|---|---|---|
| `session_id` | integer | The session to clear |

**Example Request**
```
DELETE /api/v1/ai/chat/sessions/14/clear/
```

**Response — `200 OK`**
```json
{
    "deleted_messages": 4
}
```

**Response — `404 Not Found`**
```json
{
    "error": "Session not found."
}
```

---

## How the Bot Knows Who You Are

The bot reads the authenticated user from the JWT token — no user ID is ever sent in the request body. It pulls the following at request time:

| Field | Source | Used For |
|---|---|---|
| `first_name` | `auth_user.first_name` | Addressing user by name in every response |
| `last_name` | `auth_user.last_name` | Full name in the system prompt |
| `username` | `auth_user.username` | Fallback if `first_name` is empty |
| `role` | `user_profiles.role` | Scoping what data the bot can discuss |
| `driver_status` | `user_profiles.driver_status` | Context for driver-specific questions |
| `id` | `auth_user.id` | Filtering data to the driver's own records |

---

## Conversation Memory

Each session has persistent memory backed by **`ConversationBufferWindowMemory`**.

| Property | Value |
|---|---|
| Memory type | `ConversationBufferWindowMemory` (LangChain) |
| Window size | Last **5 exchanges** (10 messages) |
| Storage | `ai_chat_messages` table in Supabase |
| Scope | Per session — different sessions are independent |
| Loaded from | DB on every request — survives server restarts |

**How it works:**
At the start of every request the server loads the session's stored messages from the database and replays them into the memory buffer. The buffer is then passed directly into the agent's prompt as a structured `Human / AI` conversation block, not as raw text. This means the bot can resolve follow-up questions like:

```
User:  How many vehicles are available?
Bot:   Hi Ahmed! There are 7 available vehicles.

User:  Which of those are diesel?          ← "those" resolved from memory
Bot:   Of the 7, 5 are diesel.

User:  Show me their registration numbers. ← "their" resolved from memory
Bot:   Here are the 5 diesel vehicles: ...
```

**Clearing memory:**
Call `DELETE /api/v1/ai/chat/sessions/<id>/clear/` to wipe a session's messages. The bot starts fresh on the next question to that session.

---

## Read-Only Safety

Write operations are blocked by **4 independent layers**. None of them rely on the AI's behaviour — all are enforced in Python or at the database level.

```
Agent generates SQL
        │
        ▼
Layer 1 – ReadOnlySQLQueryTool._run()
          Pure Python regex runs BEFORE the DB connection is opened.
          Blocks: INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE,
                  CREATE, GRANT, REVOKE, EXECUTE, CALL, MERGE,
                  REPLACE, COPY, multi-statement SQL (;…).
          Requires query to start with SELECT or WITH.
        │
        ▼
Layer 2 – ReadOnlySQLDatabaseToolkit.get_tools()
          The agent never receives the default unguarded QuerySQLDataBaseTool.
          It only gets ReadOnlySQLQueryTool, so there is no path to execute
          SQL without passing Layer 1.
        │
        ▼
Layer 3 – ReadOnlySQLCallbackHandler.on_tool_start()
          LangChain callback fires at the moment the agent emits a tool call.
          Runs the same regex independently of the tool's own _run() guard.
        │
        ▼
Layer 4 – Supabase ai_readonly DB role
          Database-level SELECT-only privileges. Even if all Python layers
          were bypassed, PostgreSQL rejects writes at the engine level.
```

**Blocked keywords (regex, case-insensitive):**
`INSERT` · `UPDATE` · `DELETE` · `DROP` · `ALTER` · `TRUNCATE` · `CREATE` · `GRANT` · `REVOKE` · `EXECUTE` · `EXEC` · `CALL` · `MERGE` · `REPLACE` · `UPSERT` · `COPY` · `VACUUM` · `REINDEX` · `CLUSTER` · `SET ROLE` · `SET SESSION` · `SET LOCAL`

---

## Role-Based Data Scope

The bot automatically adjusts what it queries based on the user's role.

### Driver
The bot only queries data belonging to that driver:
- Their own trips (`WHERE driver_id = <user_id>`)
- Their own expenses and fuel logs
- Their own inspections and leave requests
- Their own notifications

**Suggested questions:**
- "What is the status of my current trip?"
- "How many trips have I completed this month?"
- "Show me my recent fuel logs."
- "Do I have any pending leave requests?"
- "What vehicle am I assigned to?"

### Fleet Manager
Full read access to all fleet data:
- All vehicles, trips, drivers, orders
- All inspections, vehicle issues, maintenance
- All expenses, fuel logs, SOS alerts

**Suggested questions:**
- "How many vehicles are currently available?"
- "Show me all trips in progress right now."
- "Which vehicles are due for maintenance soon?"
- "Are there any unresolved SOS alerts?"
- "How many orders were delivered this week?"
- "Which driver completed the most trips this month?"
- "Show me all high-severity vehicle issues."
- "What is the total fuel cost for March?"

### Maintenance Staff
Focused on vehicle health:
- All vehicles and maintenance history
- All maintenance schedules and records
- All vehicle issues and inspections

**Suggested questions:**
- "Which vehicles have open issues?"
- "Show me all scheduled maintenance this week."
- "Which maintenance records are currently in progress?"
- "List all critical vehicle issues."
- "What spare parts were used last month?"
- "Which vehicles haven't had a service in 3 months?"

---

## What the Bot Can and Cannot Do

### Can do
- Answer questions about any data in the fleet database
- Resolve follow-up questions using conversation memory ("those", "them", "the one you mentioned")
- Compare data across time periods (e.g. "this month vs last month")
- Aggregate data (counts, sums, averages)
- Filter by status, date range, driver, vehicle, etc.

### Cannot do
- Create, update, or delete any records (blocked at 4 layers)
- Access GPS logs, odometer photos, delivery proof images (excluded for performance)
- Answer questions unrelated to fleet management
- Access data outside your role's scope (drivers cannot see other drivers' data)

---

## Session Flow (Frontend Integration)

```
1. User opens chat
   → GET /api/v1/ai/chat/sessions/
   → Render list of past sessions in sidebar

2. User starts a new chat (no session_id)
   → POST /api/v1/ai/chat/   { "message": "..." }
   → Save returned session_id for all follow-up messages in this conversation
   → Render suggested_questions as quick-reply chips

3. User sends a follow-up (pass session_id)
   → POST /api/v1/ai/chat/   { "message": "...", "session_id": 14 }
   → Bot has full memory of the last 5 exchanges automatically

4. User taps a past session
   → GET /api/v1/ai/chat/history/?session_id=14
   → Render all messages in order (role: "human" | "ai")

5. User clears the chat
   → DELETE /api/v1/ai/chat/sessions/14/clear/
   → Messages deleted, session_id still valid for new questions
```

---

## Error Reference

| HTTP Code | Meaning |
|---|---|
| `200 OK` | Success |
| `400 Bad Request` | Missing or invalid field in request body / query params |
| `401 Unauthorized` | Missing or expired JWT token |
| `404 Not Found` | `session_id` does not exist or does not belong to this user |
| `429 Too Many Requests` | Rate limit exceeded (20 requests/hour per user) |
| `503 Service Unavailable` | `MISTRAL_API_KEY` or `AI_ASSISTANT_DB_URL` not set in `.env` |
| `500 Internal Server Error` | Unexpected agent error — check server logs |

---

## Database Tables the Bot Can Query

| Table | Description |
|---|---|
| `auth_user` | Users (id, username, first_name, last_name, email) |
| `user_profiles` | Roles, driver status, phone |
| `locations` | Warehouses and drop points |
| `leave_requests` | Driver leave requests |
| `vehicles` | Vehicle master data |
| `inspection_checklists` | Checklist templates |
| `inspections` | Pre/post-trip and ad-hoc inspections |
| `vehicle_issues` | Reported vehicle problems |
| `orders` | Order master records |
| `order_drop_points` | Delivery locations per order |
| `trips` | Trip assignments and status |
| `routes` | Planned routes with distance/duration |
| `trip_expenses` | Fuel, toll, parking, other expenses |
| `fuel_logs` | Fuel fill-up records |
| `maintenance_schedules` | Scheduled preventive/corrective maintenance |
| `maintenance_records` | Actual maintenance work performed |
| `spare_parts` | Parts catalog linked to maintenance |
| `spare_parts_used` | Parts used in a specific maintenance job |
| `notifications` | System notifications per user |
| `sos_alerts` | Driver emergency alerts |

**Excluded tables** (too large / binary data / not useful for chat):
`gps_logs`, `driver_locations`, `route_deviations`, `geofence_events`, `delivery_proofs`, `odometer_images`, `inspection_results`, `messages`, `driver_documents`, `profile_images`

---

## Example Conversations

### Multi-turn follow-up (memory in action)

```
User:  How many vehicles do we have and what are their statuses?

Bot:   Hi Ahmed! Here's the current vehicle breakdown:

       Total vehicles: 12
       - Available: 7
       - In Trip: 3
       - Under Maintenance: 1
       - Idle: 1

User:  Which ones are under maintenance?      ← follow-up, no context repeated

Bot:   The vehicle currently under maintenance is:
       MH-12-ZZ-9900 – Tata Prima (2021)
       Active maintenance record started 25 Mar 2026.

User:  Who reported the issue for that vehicle?  ← chained follow-up

Bot:   The issue for MH-12-ZZ-9900 was reported by Rahul Singh (driver)
       on 24 Mar 2026 with severity: High.
```

### Driver Example

```
User:  What is the status of my current trip?

Bot:   Hi Rahul! Your current trip:

       Trip #48 — Order REF-2026-0091
       Status: In Progress
       Vehicle: MH-14-CD-5678 (Ashok Leyland)
       Started: 27 Mar 2026, 08:15 AM
       Drop points: 3 (1 delivered, 2 pending)
```

### Maintenance Staff Example

```
User:  Show me all maintenance scheduled for this week.

Bot:   Hi Priya! 3 schedules for this week (24–30 Mar 2026):

       1. MH-12-AB-1234 | Preventive | 28 Mar | Scheduled
          40,000 km oil change and filter replacement

       2. MH-10-GH-3344 | Corrective | 29 Mar | In Progress
          Brake pad replacement (from inspection #31)

       3. MH-14-CD-5678 | Emergency  | 30 Mar | Scheduled
          Engine overheating — SOS alert #7
```

---

## Postman / HTTP Client Quick Reference

### 1. Get a token
```
POST /api/v1/auth/token/
Content-Type: application/json

{
    "username": "ahmed_manager",
    "password": "yourpassword"
}
```
Copy `access` from the response. Use it as `Bearer <token>` in all AI requests.

### 2. Start a new chat
```
POST /api/v1/ai/chat/
Authorization: Bearer eyJ...
Content-Type: application/json

{
    "message": "How many trips were completed today?"
}
```

### 3. Follow-up in the same session
```
POST /api/v1/ai/chat/
Authorization: Bearer eyJ...
Content-Type: application/json

{
    "message": "Show me the driver names for those trips.",
    "session_id": 14
}
```

### 4. Load session history
```
GET /api/v1/ai/chat/history/?session_id=14
Authorization: Bearer eyJ...
```

### 5. List all past sessions
```
GET /api/v1/ai/chat/sessions/
Authorization: Bearer eyJ...
```

### 6. Clear a session
```
DELETE /api/v1/ai/chat/sessions/14/clear/
Authorization: Bearer eyJ...
```

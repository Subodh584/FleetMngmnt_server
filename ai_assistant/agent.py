"""
Fleet Management AI assistant — direct SQL chain (no ReAct agent).

Instead of a ReAct agent (which Mistral consistently fails to format),
this uses a simple 2-step approach:
  1. Ask the LLM to generate a SQL query
  2. Run the query, then ask the LLM to format a friendly answer

Usage:
    chain = build_fleet_agent(user, recent_messages)
    result = chain.invoke({"input": "How many trips completed today?"})
    answer = result["output"]
"""

import logging
import re
from collections import namedtuple
from datetime import date

from django.conf import settings
from langchain_community.utilities import SQLDatabase
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_mistralai import ChatMistralAI

from .safety import validate_read_only_sql

logger = logging.getLogger('ai_assistant')

# ---------------------------------------------------------------------------
# Tables the agent is allowed to inspect
# ---------------------------------------------------------------------------

INCLUDED_TABLES = [
    'auth_user',
    'user_profiles',
    'locations',
    'leave_requests',
    'vehicles',
    'inspection_checklists',
    'inspections',
    'vehicle_issues',
    'orders',
    'order_drop_points',
    'trips',
    'routes',
    'trip_expenses',
    'fuel_logs',
    'maintenance_schedules',
    'maintenance_records',
    'spare_parts',
    'spare_parts_used',
    'notifications',
    'sos_alerts',
]

# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """\
You are FleetBot, an AI assistant for the Fleet Management platform.
You help fleet managers, drivers, and maintenance staff query and understand fleet data.

CURRENT USER: {full_name} (username: {username}, role: {role_display}, status: {driver_status}, user_id: {user_id})
Today: {today}

{role_context}

KEY STATUS VALUES (case-sensitive, use these exact strings in WHERE clauses):
  vehicles.status: 'available' | 'in_trip' | 'idle' | 'under_maintenance'
  user_profiles.role: 'driver' | 'fleet_manager' | 'maintenance_staff'
  user_profiles.driver_status: 'available' | 'in_trip' | 'clocked_out' | 'on_rest' | 'on_leave'
  trips.status: 'pending' | 'assigned' | 'accepted' | 'in_progress' | 'completed' | 'cancelled' | 'rejected' | 'delayed'
  orders.status: 'pending' | 'assigned' | 'in_transit' | 'delivered' | 'failed'
  order_drop_points.status: 'pending' | 'in_transit' | 'arrived' | 'delivered' | 'failed'
  inspections.inspection_type: 'pre_trip' | 'post_trip' | 'ad_hoc'
  inspections.overall_status: 'pending' | 'approved' | 'flagged' | 'maintenance_scheduled'
  vehicle_issues.severity: 'low' | 'medium' | 'high' | 'critical'
  vehicle_issues.status: 'reported' | 'acknowledged' | 'in_repair' | 'resolved'
  leave_requests.status: 'pending' | 'approved' | 'rejected'
  maintenance_schedules.status: 'scheduled' | 'in_progress' | 'completed' | 'cancelled'
  maintenance_schedules.maintenance_type: 'preventive' | 'corrective' | 'emergency'
  maintenance_records.repair_status: 'pending' | 'in_progress' | 'completed' | 'cancelled'
  notifications.alert_type: 'sos' | 'route_deviation' | 'geofence_entry' | 'geofence_exit' | 'maintenance_due' | 'issue_reported' | 'trip_rejected' | 'leave_approved' | 'leave_rejected' | 'leave_request'
  notifications.status: 'unread' | 'read'
  trip_expenses.expense_type: 'fuel' | 'toll' | 'parking' | 'other'

RULES:
  1. Always address the user by their first name ({first_name}).
  2. Format currency in INR (₹). When showing trips, join auth_user for driver names.
  3. Use exact status values above in WHERE clauses (e.g. WHERE status = 'under_maintenance', NOT 'maintenance').
  4. The database timezone is Asia/Kolkata (IST, UTC+5:30).
  5. If a question is outside fleet data scope, politely decline.
"""

_DRIVER_CONTEXT = """\
DATA SCOPE (Driver):
  You are speaking to a driver. Show ONLY their own data:
  - Their trips: WHERE driver_id = {user_id}
  - Their expenses and fuel logs: WHERE driver_id = {user_id}
  - Their inspections: WHERE driver_id = {user_id}
  - Their leave requests: WHERE driver_id = {user_id}
  - Their notifications: WHERE user_id = {user_id}
  - Vehicles assigned to their active/recent trips only
  Do NOT expose other drivers' personal details."""

_FLEET_MANAGER_CONTEXT = """\
DATA SCOPE (Fleet Manager):
  You have full visibility of all fleet data:
  - All vehicles, trips, drivers, orders
  - All inspections, vehicle issues, maintenance records
  - All expenses, fuel logs, leave requests
  - All SOS alerts and notifications"""

_MAINTENANCE_CONTEXT = """\
DATA SCOPE (Maintenance Staff):
  Your focus is vehicle health and maintenance:
  - All vehicles and their maintenance history
  - All maintenance schedules and records
  - All vehicle issues and inspections
  - You may reference trips and drivers for context"""


def _build_system_prompt(user) -> str:
    """Compose the full system prompt for the given user."""
    profile = getattr(user, 'profile', None)
    role = profile.role if profile else 'unknown'
    driver_status = profile.driver_status if profile else 'N/A'

    role_display = role.replace('_', ' ').title()
    status_display = driver_status.replace('_', ' ').title()
    first_name = user.first_name or user.username

    if role == 'driver':
        role_context = _DRIVER_CONTEXT.format(user_id=user.id)
    elif role == 'fleet_manager':
        role_context = _FLEET_MANAGER_CONTEXT
    else:
        role_context = _MAINTENANCE_CONTEXT

    return _SYSTEM_PROMPT.format(
        full_name=f"{user.first_name} {user.last_name}".strip() or user.username,
        first_name=first_name,
        username=user.username,
        role_display=role_display,
        driver_status=status_display,
        user_id=user.id,
        today=date.today().strftime('%A, %d %B %Y'),
        role_context=role_context,
    )


def _format_chat_history(recent_messages, window: int) -> str:
    """Format recent messages as a simple text conversation history."""
    messages = list(recent_messages or [])[-window:]
    if not messages:
        return '(no previous messages)'

    lines = []
    for msg in messages:
        role = 'User' if msg.role == 'human' else 'FleetBot'
        lines.append(f"{role}: {msg.content}")
    return '\n'.join(lines)


def _clean_sql(raw: str) -> str:
    """Strip markdown fences and whitespace from LLM SQL output."""
    raw = re.sub(r'```sql\s*', '', raw)
    raw = re.sub(r'```\s*', '', raw)
    raw = raw.strip().rstrip(';')
    return raw


# ---------------------------------------------------------------------------
# FleetAssistantChain — replaces the broken ReAct agent
# ---------------------------------------------------------------------------

_Action = namedtuple('Action', ['tool', 'tool_input'])


class FleetAssistantChain:
    """
    Simple 2-step chain that replaces the ReAct SQL agent.

    Step 1: LLM generates a SQL query (or decides no SQL is needed).
    Step 2: SQL is validated, executed, then LLM formats the answer.

    This avoids all ReAct output parsing issues with Mistral.
    """

    def __init__(self, llm, db, system_prompt, chat_history, first_name):
        self.llm = llm
        self.db = db
        self.system_prompt = system_prompt
        self.chat_history = chat_history
        self.first_name = first_name
        self._schema = None

    def _get_schema(self):
        if self._schema is None:
            self._schema = self.db.get_table_info()
        return self._schema

    def invoke(self, inputs, config=None):
        user_message = inputs['input']
        schema = self._get_schema()

        # ── Step 1: Generate SQL ────────────────────────────────────────
        sql_messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=(
                f"DATABASE SCHEMA:\n{schema}\n\n"
                f"CONVERSATION HISTORY:\n{self.chat_history}\n\n"
                f"USER QUESTION: {user_message}\n\n"
                "Write a single PostgreSQL SELECT query to answer the question above.\n"
                "Return ONLY the raw SQL query — no explanation, no markdown fences.\n"
                "If the question cannot be answered with SQL (e.g. it's a greeting or "
                "off-topic), return exactly: NO_SQL_NEEDED"
            )),
        ]

        sql_response = self.llm.invoke(sql_messages).content.strip()
        logger.info("SQL generation response: %s", sql_response[:200])

        # ── Handle non-SQL questions ────────────────────────────────────
        if 'NO_SQL_NEEDED' in sql_response:
            answer_messages = [
                SystemMessage(content=self.system_prompt),
                HumanMessage(content=(
                    f"CONVERSATION HISTORY:\n{self.chat_history}\n\n"
                    f"The user said: {user_message}\n\n"
                    "This question doesn't require a database query. "
                    "Provide a helpful, friendly response. Keep it concise."
                )),
            ]
            answer = self.llm.invoke(answer_messages).content.strip()
            return {'output': answer, 'intermediate_steps': []}

        # ── Clean and validate SQL ──────────────────────────────────────
        raw_sql = _clean_sql(sql_response)
        validate_read_only_sql(raw_sql)

        # ── Execute SQL ─────────────────────────────────────────────────
        try:
            query_result = self.db.run(raw_sql)
        except Exception as e:
            logger.warning("SQL execution failed: %s — query: %s", e, raw_sql)
            # Give the LLM a second chance with the error
            retry_messages = [
                SystemMessage(content=self.system_prompt),
                HumanMessage(content=(
                    f"DATABASE SCHEMA:\n{schema}\n\n"
                    f"USER QUESTION: {user_message}\n\n"
                    f"I tried this SQL query:\n{raw_sql}\n\n"
                    f"But it failed with error: {e}\n\n"
                    "Please write a corrected PostgreSQL SELECT query. "
                    "Return ONLY the raw SQL — no explanation."
                )),
            ]
            retry_response = self.llm.invoke(retry_messages).content.strip()
            raw_sql = _clean_sql(retry_response)
            validate_read_only_sql(raw_sql)
            query_result = self.db.run(raw_sql)

        logger.info("Executed SQL: %s", raw_sql)
        logger.info("Query result preview: %s", str(query_result)[:300])

        # ── Step 2: Format the answer ───────────────────────────────────
        answer_messages = [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=(
                f"CONVERSATION HISTORY:\n{self.chat_history}\n\n"
                f"The user asked: {user_message}\n\n"
                f"I ran this SQL query:\n{raw_sql}\n\n"
                f"Query result:\n{query_result}\n\n"
                "Based on the query result, give a clear, friendly, and accurate answer. "
                f"Address the user as {self.first_name}. "
                "Format numbers nicely. If it's a list, present it in a readable way. "
                "If the result is empty, explain that politely. "
                "Do NOT include the SQL query in your response."
            )),
        ]

        answer = self.llm.invoke(answer_messages).content.strip()

        # Build intermediate_steps so extract_generated_sql() still works
        intermediate_steps = [(_Action(tool='sql_db_query', tool_input=raw_sql), query_result)]
        return {'output': answer, 'intermediate_steps': intermediate_steps}


# ---------------------------------------------------------------------------
# Public API (same interface as before)
# ---------------------------------------------------------------------------

def build_fleet_agent(user, recent_messages=None):
    """
    Build and return a FleetAssistantChain.

    Args:
        user: Django User instance (must have .profile OneToOneField)
        recent_messages: Iterable of AIChatMessage ORM objects (ordered oldest-first).

    Returns:
        FleetAssistantChain. Invoke with {'input': user_message}.
    """
    history_window = getattr(settings, 'AI_CHAT_HISTORY_WINDOW', 10)
    model_name = getattr(settings, 'MISTRAL_MODEL', 'mistral-large-latest')
    db_url = getattr(settings, 'AI_ASSISTANT_DB_URL', '')

    if not db_url:
        raise ValueError(
            "AI_ASSISTANT_DB_URL is not configured. "
            "Set it in your .env file to a read-only Supabase connection string."
        )

    llm = ChatMistralAI(
        model=model_name,
        api_key=settings.MISTRAL_API_KEY,
        temperature=0,
        max_tokens=2048,
    )

    db = SQLDatabase.from_uri(
        db_url,
        include_tables=INCLUDED_TABLES,
        sample_rows_in_table_info=3,
        engine_args={
            'pool_pre_ping': True,
            'pool_size': 2,
            'max_overflow': 3,
            'connect_args': {'connect_timeout': 10},
        },
    )

    system_prompt = _build_system_prompt(user)
    chat_history = _format_chat_history(recent_messages, history_window)
    first_name = user.first_name or user.username

    return FleetAssistantChain(
        llm=llm,
        db=db,
        system_prompt=system_prompt,
        chat_history=chat_history,
        first_name=first_name,
    )


def extract_generated_sql(result: dict) -> str:
    """Extract the last SQL query executed from the intermediate steps."""
    steps = result.get('intermediate_steps', [])
    for action, _observation in reversed(steps):
        if hasattr(action, 'tool') and action.tool == 'sql_db_query':
            return str(action.tool_input)
    return ''

"""
SQL safety layer for the AI assistant.

Defence layers (innermost to outermost):
  1. ReadOnlySQLQueryTool  – subclass of the real query tool; validate_read_only_sql()
                             runs inside _run() BEFORE any database connection is made.
                             This is code-level enforcement — the AI has no involvement.
  2. ReadOnlySQLDatabaseToolkit – replaces the default QuerySQLDataBaseTool in the
                             toolkit with ReadOnlySQLQueryTool so the agent never
                             receives an unguarded query tool.
  3. ReadOnlySQLCallbackHandler – LangChain callback that validates again at the
                             moment the agent emits a tool call (belt-and-suspenders).
  4. Supabase ai_readonly DB role – database-level SELECT-only privileges; even if
                             all Python layers were bypassed the DB would reject writes.

validate_read_only_sql() is pure regex — it never calls the AI.
"""

import re

from django.core.exceptions import PermissionDenied
from langchain_community.agent_toolkits.sql.toolkit import SQLDatabaseToolkit
from langchain_community.tools.sql_database.tool import QuerySQLDataBaseTool
from langchain_core.callbacks import BaseCallbackHandler

# ---------------------------------------------------------------------------
# Regex patterns
# ---------------------------------------------------------------------------

# Every SQL keyword that can mutate data or schema
_BLOCKED_KEYWORDS = re.compile(
    r'\b('
    r'INSERT|UPDATE|DELETE|DROP|ALTER|TRUNCATE|CREATE|GRANT|REVOKE'
    r'|EXECUTE|EXEC|CALL|MERGE|REPLACE|UPSERT|COPY'
    r'|VACUUM|ANALYZE|REINDEX|CLUSTER'
    r'|SET\s+ROLE|SET\s+SESSION|SET\s+LOCAL'
    r')\b',
    re.IGNORECASE,
)

# Semicolon followed by anything — blocks chained statements (SELECT 1; DELETE …)
_MULTI_STATEMENT = re.compile(r';.+\S', re.DOTALL)

# Query must begin with SELECT or a CTE (WITH … SELECT …)
_ALLOWED_START = re.compile(r'^\s*(SELECT|WITH)\b', re.IGNORECASE)


# ---------------------------------------------------------------------------
# Core validator — pure regex, zero AI involvement
# ---------------------------------------------------------------------------

def validate_read_only_sql(sql: str) -> str:
    """
    Raise PermissionDenied if the SQL contains any write or DDL keyword,
    chains statements with a semicolon, or does not start with SELECT/WITH.

    This function is intentionally dumb and fast: it does plain regex matching
    on the raw SQL string. It does NOT call the AI or any external service.

    Returns the original sql string unchanged if all checks pass.
    """
    if not sql or not sql.strip():
        raise PermissionDenied("Blocked: empty SQL query.")

    if _BLOCKED_KEYWORDS.search(sql):
        raise PermissionDenied(
            "Blocked by read-only policy: write or DDL keyword detected."
        )

    if _MULTI_STATEMENT.search(sql):
        raise PermissionDenied(
            "Blocked by read-only policy: multi-statement SQL is not allowed."
        )

    if not _ALLOWED_START.match(sql):
        raise PermissionDenied(
            "Blocked by read-only policy: only SELECT statements are permitted."
        )

    return sql


# ---------------------------------------------------------------------------
# Layer 1 — Override the query tool itself
# ---------------------------------------------------------------------------

class ReadOnlySQLQueryTool(QuerySQLDataBaseTool):
    """
    Drop-in replacement for QuerySQLDataBaseTool.

    validate_read_only_sql() is called inside _run() — the method that actually
    opens a database connection and sends the query. This happens before any
    network I/O, purely in Python, with no AI involvement.

    Even if the LangChain callback system is disabled or bypassed, this tool
    will still refuse to execute any non-SELECT query.
    """

    def _run(self, query: str, run_manager=None) -> str:
        # Hard block — pure regex, runs before the DB connection is touched
        validate_read_only_sql(query)
        return super()._run(query, run_manager=run_manager)


# ---------------------------------------------------------------------------
# Layer 2 — Toolkit that never exposes the unguarded query tool
# ---------------------------------------------------------------------------

class ReadOnlySQLDatabaseToolkit(SQLDatabaseToolkit):
    """
    SQLDatabaseToolkit subclass that replaces the default QuerySQLDataBaseTool
    with ReadOnlySQLQueryTool in get_tools(). The agent therefore never
    receives a tool that can execute writes.
    """

    def get_tools(self):
        tools = super().get_tools()
        return [
            ReadOnlySQLQueryTool(db=self.db) if isinstance(t, QuerySQLDataBaseTool) else t
            for t in tools
        ]


# ---------------------------------------------------------------------------
# Layer 3 — Callback handler (belt-and-suspenders)
# ---------------------------------------------------------------------------

class ReadOnlySQLCallbackHandler(BaseCallbackHandler):
    """
    LangChain event callback that fires every time the agent starts a tool call.
    Re-runs validate_read_only_sql() at the callback level as a second check,
    independently of the tool's own _run() guard.
    """

    def on_tool_start(self, serialized, input_str, **kwargs):
        tool_name = serialized.get('name', '')
        if tool_name == 'sql_db_query':
            validate_read_only_sql(str(input_str))

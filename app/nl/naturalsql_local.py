import re
from dataclasses import dataclass
from app.nl.model_loader import generate

# ---------------------------------------------------------------------
# Prompt template and schema
# ---------------------------------------------------------------------

# A concise SQLite schema for prompt
DDL = """\
CREATE TABLE users (
  user_id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  email TEXT NOT NULL UNIQUE,
  mfa_enabled BOOLEAN,
  last_login TIMESTAMP,
  status TEXT,
  groups TEXT
);
CREATE TABLE devices (
  device_id TEXT PRIMARY KEY,
  hostname TEXT NOT NULL,
  ip_address TEXT,
  os TEXT,
  assigned_user TEXT,
  location TEXT,
  encryption BOOLEAN,
  status TEXT,
  last_checkin TIMESTAMP
);
CREATE TABLE apps (
  app_id INTEGER PRIMARY KEY,
  name TEXT NOT NULL UNIQUE,
  owner TEXT,
  type TEXT
);
CREATE TABLE user_apps (
  user_id TEXT,
  app_name TEXT,
  PRIMARY KEY (user_id, app_name)
);
"""

# Restrict generated queries to these tables only.
ALLOW_TABLES = {"users", "devices", "apps", "user_apps"}

# Base system prompt
SYSTEM = (
    "Generate a single SQLite SELECT query (no comments) that answers the question.\n"
    "Use ONLY the following schema:\n"
    f"{DDL}\n"
    "Rules:\n"
    "- Exactly one SELECT statement (no INSERT/UPDATE/DELETE/DDL; no multiple statements).\n"
    "- Avoid Postgres-only syntax (ILIKE, ::type, NULLS FIRST/LAST).\n"
    "- Return ONLY the SQL; if you add fences, use ```sql ... ```.\n"
)

def build_prompt(question: str) -> str:
    """Build the full prompt sent to the model."""
    return f"{SYSTEM}\nQuestion: {question}\nSQL:\n```sql\n"


# ---------------------------------------------------------------------
# Guardrail helpers
# ---------------------------------------------------------------------

@dataclass
class SqlCheck:
    """Container for the result of SQL validation."""
    ok: bool
    reason: str | None = None
    sql: str | None = None

def _extract_sql(text: str) -> str:
    """Extract the SQL code block (```sql ... ```), or raw text if not fenced."""
    m = re.search(r"```sql\s*(.*?)```", text, flags=re.S | re.I)
    out = m.group(1).strip() if m else text.strip()
    # Drop accidental labels like 'SQL:' at the start.
    return re.sub(r"^\s*sql\s*:\s*", "", out, flags=re.I)

def _is_single_statement(sql: str) -> bool:
    """Ensure there is at most one statement (semicolon count)."""
    return sql.strip().count(";") <= 1

def _only_select(sql: str) -> bool:
    """Require the statement to start with SELECT."""
    return re.match(r"^\s*select\b", sql, flags=re.I) is not None

def _patch_postgresisms(sql: str) -> str:
    """Replace or remove Postgres-specific syntax to keep it SQLite-safe."""
    sql = re.sub(r"\bilike\b", "like", flags=re.I, string=sql)
    sql = re.sub(r"::\s*\w+", "", sql)
    sql = re.sub(r"\s+nulls\s+(last|first)", "", flags=re.I, string=sql)
    return sql

def _allowlisted_tables(sql: str) -> bool:
    """Verify every FROM/JOIN table is in the allowlist."""
    tables = set()
    for a, b in re.findall(r"\bfrom\s+([a-zA-Z_]\w*)|\bjoin\s+([a-zA-Z_]\w*)", sql, flags=re.I):
        if a: tables.add(a.lower())
        if b: tables.add(b.lower())
    return all(t in ALLOW_TABLES for t in tables)

def _force_limit(sql: str, limit: int) -> str:
    """Append a LIMIT clause if none exists."""
    if re.search(r"\blimit\s+\d+\b", sql, flags=re.I):
        return sql
    return f"{sql}\nLIMIT {limit}"

def sanitize_sql(sql: str, limit: int) -> SqlCheck:
    """
    Validate and lightly rewrite the generated SQL.
    Ensures: single statement, SELECT only, allow-listed tables,
    and guarantees a LIMIT clause.
    """
    raw = sql.strip().rstrip(";")
    if not _is_single_statement(raw):
        return SqlCheck(False, "multiple statements not allowed")
    if not _only_select(raw):
        return SqlCheck(False, "only SELECT allowed")
    patched = _patch_postgresisms(raw)
    if not _allowlisted_tables(patched):
        return SqlCheck(False, "uses non-allowlisted table(s)")
    final = _force_limit(patched, limit)
    return SqlCheck(True, sql=final)


# ---------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------

def generate_sql(question: str, limit: int = 100) -> str:
    """
    Turn a natural language question into a safe SQLite SELECT statement.
    1. Build a schema-aware prompt
    2. Call the local language model
    3. Extract and validate the SQL
    """
    prompt = build_prompt(question)
    # print("Prompt:", prompt)
    gen = generate(prompt, max_new_tokens=128)
    # print("Generated text:", gen)
    sql = _extract_sql(gen)
    # print("Extracted SQL:", sql)
    check = sanitize_sql(sql, limit=limit)
    if not check.ok:
        raise ValueError(f"Unsafe SQL: {check.reason}")
    return check.sql

# app/nl/naturalsql_local.py
import re
from dataclasses import dataclass
from app.nl.model_loader import generate

# Keep schema brief to avoid long prompts
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

ALLOW_TABLES = {"users", "devices", "apps", "user_apps"}

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
    return f"{SYSTEM}\nQuestion: {question}\nSQL:\n```sql\n"

# --------- Guardrails ---------
@dataclass
class SqlCheck:
    ok: bool
    reason: str | None = None
    sql: str | None = None

def _extract_sql(text: str) -> str:
    m = re.search(r"```sql\s*(.*?)```", text, flags=re.S | re.I)
    out = m.group(1).strip() if m else text.strip()
    # drop stray leading labels like 'SQL:' if present
    out = re.sub(r"^\s*sql\s*:\s*", "", out, flags=re.I)
    return out

def _is_single_statement(sql: str) -> bool:
    return sql.strip().count(";") <= 1

def _only_select(sql: str) -> bool:
    return re.match(r"^\s*select\b", sql, flags=re.I) is not None

def _patch_postgresisms(sql: str) -> str:
    sql = re.sub(r"\bilike\b", "like", flags=re.I, string=sql)
    sql = re.sub(r"::\s*\w+", "", sql)
    sql = re.sub(r"\s+nulls\s+(last|first)", "", flags=re.I, string=sql)
    return sql

def _allowlisted_tables(sql: str) -> bool:
    tables = set()
    for a, b in re.findall(r"\bfrom\s+([a-zA-Z_]\w*)|\bjoin\s+([a-zA-Z_]\w*)", sql, flags=re.I):
        if a: tables.add(a.lower())
        if b: tables.add(b.lower())
    return all(t in ALLOW_TABLES for t in tables)

def _force_limit(sql: str, limit: int) -> str:
    if re.search(r"\blimit\s+\d+\b", sql, flags=re.I):
        return sql
    return f"{sql}\nLIMIT {limit}"

def sanitize_sql(sql: str, limit: int) -> SqlCheck:
    raw = sql.strip().rstrip(";")
    if not _is_single_statement(raw):      return SqlCheck(False, "multiple statements not allowed")
    if not _only_select(raw):              return SqlCheck(False, "only SELECT allowed")
    patched = _patch_postgresisms(raw)
    if not _allowlisted_tables(patched):   return SqlCheck(False, "uses non-allowlisted table(s)")
    final = _force_limit(patched, limit)
    return SqlCheck(True, sql=final)

# --------- Public API ----------
def generate_sql(question: str, limit: int = 100) -> str:
    # print("Question:", question)
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

from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.db import get_db
from app.nl.naturalsql_local import generate_sql

# --------------------------------------------------------------------
# Router setup
# --------------------------------------------------------------------
router = APIRouter(prefix="", tags=["ask"])


# Request schema: simple question + optional limit
class AskRequest(BaseModel):
    q: str               # natural-language question
    limit: int | None = 100  # optional row cap (defaults to 100)


@router.post("/ask")
def ask(req: AskRequest, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Accept a natural-language question, convert it to SQL, execute it,
    and return both the generated SQL and the result rows.

    Request body:
      {"q": "Which users don't have MFA?", "limit": 100}

    Response JSON:
      {
        "ok": True,
        "provider": "local-naturalsql",
        "sql": "<generated SELECT statement>",
        "rows": [ {column: value, ...}, ... ]
      }
    """
    # Trim and validate the question
    question = (req.q or "").strip()
    if not question:
        raise HTTPException(400, "Missing 'q'")

    try:
        # Clamp limit to 1–200 for safety
        lim = 1 if not req.limit else max(1, min(int(req.limit), 200))

        # Use the local NL->SQL generator to build a safe SELECT statement
        sql = generate_sql(question, limit=lim)

        # Execute the query in read-only mode and fetch as dicts
        result = db.execute(text(sql)).mappings().all()
        rows: List[Dict[str, Any]] = [dict(m) for m in result]

        return {"ok": True, "provider": "local-naturalsql", "sql": sql, "rows": rows}

    except Exception as e:
        # Unfortunately this happens a decent amount due to the limitations of the nl->sql model
        raise HTTPException(400, f"Could not answer: {e}")

# app/routers/ask.py
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.db import get_db
from app.nl.naturalsql_local import generate_sql

router = APIRouter(prefix="", tags=["ask"])

class AskRequest(BaseModel):
    q: str
    limit: int | None = 100

@router.post("/ask")
def ask(req: AskRequest, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Body: {"q": "...", "limit": 100}
    Returns: {"ok": True, "provider": "local-naturalsql", "sql": "...", "rows": [...]}
    """
    question = (req.q or "").strip()
    if not question:
        raise HTTPException(400, "Missing 'q'")

    try:
        lim = 1 if not req.limit else max(1, min(int(req.limit), 200))
        sql = generate_sql(question, limit=lim)

        # Read-only execution
        result = db.execute(text(sql)).mappings().all()  # list[RowMapping]
        print(result)
        rows: List[Dict[str, Any]] = [dict(m) for m in result]

        return {"ok": True, "provider": "local-naturalsql", "sql": sql, "rows": rows}
    except Exception as e:
        # Surface the SQL and error to the client for debugging
        raise HTTPException(400, f"Could not answer: {e}")

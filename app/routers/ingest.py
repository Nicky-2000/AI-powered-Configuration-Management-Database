from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db import get_db
from app.repositories import update_or_insert_devices, update_or_insert_okta
from app.normalizers import get_default_normalizer

router = APIRouter(prefix="", tags=["ingest"])

@router.post("/ingest")
def ingest(payload: list[dict], db: Session = Depends(get_db)):
    if not isinstance(payload, list) or not payload:
        raise HTTPException(400, "Payload must be a non-empty JSON array")

    first = payload[0]
    try:
        if "device_id" in first and "hostname" in first:
            ok, errors = update_or_insert_devices(db, payload, normalizer=get_default_normalizer())
            db.commit()
            return {"ok": True, "source": "hardware", "ingested": ok, "failed": len(errors),
                    "errors": errors[:10]}  # cap error list
        elif "user_id" in first and "email" in first:
            ok, errors = update_or_insert_okta(db, payload, normalizer=get_default_normalizer())
            db.commit()
            return {"ok": True, "source": "okta", "ingested": ok, "failed": len(errors),
                    "errors": errors[:10]}
    except ValueError as e:
        db.rollback()
        raise HTTPException(400, str(e))
    except Exception as e:
        db.rollback()
        raise HTTPException(500, f"Ingest failed: {e}")

    raise HTTPException(400, "Unknown payload type (expect hardware devices or Okta users).")

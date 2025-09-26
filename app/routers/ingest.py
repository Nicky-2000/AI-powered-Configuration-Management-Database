from typing import List, Dict
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.repositories import update_or_insert_devices, update_or_insert_okta
from app.normalizers import get_default_normalizer

# --------------------------------------------------------------------
# Router setup
# --------------------------------------------------------------------
router = APIRouter(prefix="", tags=["ingest"])


def _kind_of(item: Dict) -> str | None:
    """
    Quick classifier for incoming records.
    Returns:
      "hardware" if it looks like a device record,
      "okta" if it looks like an Okta user record,
      None if it doesn't match either schema.
      
      This can be expanded to add more data types in the future.
    """
    if "device_id" in item and "hostname" in item:
        return "hardware"
    if "user_id" in item and "email" in item:
        return "okta"
    return None


@router.post("/ingest")
def ingest(payload: List[Dict], db: Session = Depends(get_db)):
    """
    Bulk-ingest hardware devices or Okta user records.

    Accepts:
        A JSON array of objects. Each object must match either
        the "hardware" schema (device_id + hostname) or the
        "okta" schema (user_id + email).

    Behavior:
        * Homogeneous payload (all hardware or all okta):
          → single bulk insert/update for speed.
        * Mixed payload:
          → processes each record individually so one bad record
            doesn’t block others.

    Returns:
        {
          "ok": True,
          "source": "hardware" | "okta" | "mixed",
          "ingested": <count of successful rows>,
          "failed": <count of failed rows>,
          "errors": [ ... up to 10 sample errors ... ]
        }
    """
    # Validate top-level structure
    if not isinstance(payload, list) or not payload:
        raise HTTPException(400, "Payload must be a non-empty JSON array")

    normalizer = get_default_normalizer()

    # Determine what kinds of records we have
    kinds = { _kind_of(p) for p in payload }
    if None in kinds:
        # At least one record doesn't match either schema
        raise HTTPException(400, "Unknown record in payload (not hardware or okta)")
    kinds.discard(None)  # just to be safe

    try:
        # Fast path: all records are the same kind
        if len(kinds) == 1:
            kind = next(iter(kinds))
            if kind == "hardware":
                ok, errors = update_or_insert_devices(db, payload, normalizer=normalizer)
                db.commit()
                return {
                    "ok": True,
                    "source": "hardware",
                    "ingested": ok,
                    "failed": len(errors),
                    "errors": errors[:10],  # limit size of error list
                }
            else:  # "okta"
                ok, errors = update_or_insert_okta(db, payload, normalizer=normalizer)
                db.commit()
                return {
                    "ok": True,
                    "source": "okta",
                    "ingested": ok,
                    "failed": len(errors),
                    "errors": errors[:10],
                }

        # Mixed path: handle each record separately. 
        # Commit successes one at a time so a bad record won’t abort the whole batch.
        ingested = 0
        errors: List[Dict] = []

        for rec in payload:
            kind = _kind_of(rec)
            try:
                if kind == "hardware":
                    ok, errs = update_or_insert_devices(db, [rec], normalizer=normalizer)
                else:  # "okta"
                    ok, errs = update_or_insert_okta(db, [rec], normalizer=normalizer)

                if ok == 1 and not errs:
                    db.commit()
                    ingested += 1
                else:
                    db.rollback()
                    errors.extend(errs or [{"error": "Unknown validation error", "record": rec}])
            except Exception as e:
                # Roll back this record and log the failure
                db.rollback()
                errors.append({"error": str(e), "record": rec})

        return {
            "ok": True,
            "source": "mixed",
            "ingested": ingested,
            "failed": len(errors),
            "errors": errors[:10],
        }

    # ------------------------------------------------------------
    # Global error handling
    # ------------------------------------------------------------
    except ValueError as e:
        db.rollback()
        raise HTTPException(400, str(e))
    except Exception as e:
        db.rollback()
        raise HTTPException(500, f"Ingest failed: {e}")

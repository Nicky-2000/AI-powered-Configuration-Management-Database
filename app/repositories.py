import logging
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError, StatementError
from sqlalchemy.orm import Session
from app.models import Device, User
from app.normalizers import get_default_normalizer

log = logging.getLogger(__name__)

def update_or_insert_devices(
    db: Session, records: list[dict], normalizer=None
) -> tuple[int, list[dict]]:
    """
    Idempotent upsert by *device_id only*. Hostnames are allowed to collide.
    If device_id exists -> update that row; else create a new row.
    """
    normalizer = normalizer or get_default_normalizer()
    ok = 0
    errors: list[dict] = []

    for r in records:
        did  = (r.get("device_id") or "").strip()
        host = (r.get("hostname")  or "").strip()
        if not did or not host:
            msg = "device_id and hostname are required"
            log.warning("device record rejected: %s", msg)
            errors.append({"kind": "device", "device_id": did, "hostname": host, "error": msg})
            continue

        norm = normalizer.normalize_record("device", r)

        try:
            # per-record savepoint so one bad record doesn’t poison the batch
            with db.begin_nested():
                row = db.get(Device, did)
                if row is None:
                    row = Device(device_id=did)

                # No hostname de-duplication: collisions are allowed
                row.hostname      = host
                row.ip_address    = norm.get("ip_address")
                row.os            = norm.get("os")
                row.assigned_user = norm.get("assigned_user")
                row.location      = norm.get("location")
                row.encryption    = norm.get("encryption")
                row.status        = norm.get("status")
                row.last_checkin  = norm.get("last_checkin")

                db.merge(row)
            ok += 1

        except (IntegrityError, StatementError, TypeError, ValueError) as e:
            db.rollback()
            log.exception("device upsert failed: device_id=%s hostname=%s", did, host)
            errors.append({"kind": "device", "device_id": did, "hostname": host, "error": str(e)})

    return ok, errors



def update_or_insert_okta(db: Session, records: list[dict], normalizer=None) -> tuple[int, list[dict]]:
    normalizer = normalizer or get_default_normalizer()
    ok = 0
    errors: list[dict] = []

    for r in records:
        norm  = normalizer.normalize_record("user", r)
        uid   = (norm.get("user_id") or r.get("user_id") or "").strip()
        email = (norm.get("email") or "").strip().lower()
        name  = (norm.get("name")  or "").strip()
        if not uid or not email or not name:
            msg = "user_id, email, and name are required"
            log.warning("okta record rejected: %s (uid=%s email=%s)", msg, uid, email)
            errors.append({"kind":"user","user_id":uid,"email":email,"error":msg})
            continue

        try:
            with db.begin_nested():  # savepoint
                # resolve identity
                row = db.get(User, uid)
                email_owner = db.execute(select(User).where(User.email == email)).scalar_one_or_none()

                if row is None and email_owner is None:
                    row = User(user_id=uid, email=email, name=name)
                elif row is None and email_owner is not None:
                    log.warning("email already exists, adopting existing row; email=%s new_uid=%s old_uid=%s",
                                email, uid, email_owner.user_id)
                    row = email_owner
                elif row is not None and email_owner is not None and email_owner.user_id != row.user_id:
                    log.warning("email conflict, using email owner; email=%s incoming_uid=%s owner_uid=%s",
                                email, uid, email_owner.user_id)
                    row = email_owner

                # update fields
                row.name        = name
                row.email       = email
                row.mfa_enabled = bool(r.get("mfa_enabled")) if r.get("mfa_enabled") is not None else None
                row.last_login  = norm.get("last_login")
                row.status      = norm.get("status")
                groups          = r.get("groups") or []
                row.groups      = ",".join(groups) if groups else None
                db.merge(row)

                # apps & links
                for app_name in (r.get("apps") or []):
                    app_name = str(app_name).strip()
                    if not app_name:
                        continue
                    if not db.execute(text("SELECT 1 FROM apps WHERE name=:n"), {"n": app_name}).first():
                        db.execute(text("INSERT INTO apps(name) VALUES (:n)"), {"n": app_name})
                    if not db.execute(text(
                        "SELECT 1 FROM user_apps WHERE user_id=:u AND app_name=:a"),
                        {"u": row.user_id, "a": app_name}).first():
                        db.execute(text(
                            "INSERT INTO user_apps(user_id, app_name) VALUES (:u, :a)"),
                            {"u": row.user_id, "a": app_name})

            ok += 1
        except (IntegrityError, StatementError, TypeError, ValueError) as e:
            db.rollback()
            log.exception("okta upsert failed: uid=%s email=%s", uid, email)
            errors.append({"kind":"user","user_id":uid,"email":email,"error":str(e)})

    return ok, errors

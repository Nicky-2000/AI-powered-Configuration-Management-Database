from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.db import get_db
from app.models import User, Device, App, UserApp

router = APIRouter(prefix="", tags=["read"])

# -------------------------------------------------------------------
# Helper serializers: turn ORM objects into plain dicts for JSON
# -------------------------------------------------------------------
def _user_to_dict(u: User, db: Session) -> Dict[str, Any]:
    """Return a user row plus related apps and device IDs."""
    app_names = [ua.app_name for ua in db.query(UserApp).filter(UserApp.user_id == u.user_id).all()]
    devices = db.query(Device).filter(Device.assigned_user == u.user_id).all()
    return {
        "user_id": u.user_id,
        "name": u.name,
        "email": u.email,
        "mfa_enabled": u.mfa_enabled,
        "last_login": u.last_login,
        "status": u.status,
        "groups": u.groups,
        "apps": app_names,
        "devices": [d.device_id for d in devices],
    }

def _device_to_dict(d: Device, db: Session) -> Dict[str, Any]:
    """Return a device row and, if present, basic info about the assigned user."""
    user = None
    if d.assigned_user:
        u = db.query(User).filter(User.user_id == d.assigned_user).first()
        if u:
            user = {"user_id": u.user_id, "name": u.name, "email": u.email}
    return {
        "device_id": d.device_id,
        "hostname": d.hostname,
        "ip_address": d.ip_address,
        "os": d.os,
        "assigned_user": d.assigned_user,
        "assigned_user_details": user,
        "location": d.location,
        "encryption": d.encryption,
        "status": d.status,
        "last_checkin": d.last_checkin,
    }

def _app_to_dict(a: App, db: Session) -> Dict[str, Any]:
    """Return an app row plus IDs of users who have it."""
    uids = [ua.user_id for ua in db.query(UserApp).filter(UserApp.app_name == a.name).all()]
    return {
        "app_id": a.app_id,
        "name": a.name,
        "owner": a.owner,
        "type": a.type,
        "users": uids,
    }

# -------------------------------------------------------------------
# List endpoints
# -------------------------------------------------------------------
@router.get("/users")
def list_users(
    status: Optional[str] = Query(None, description="Exact user status match"),
    mfa: Optional[bool] = Query(None, description="True/False for MFA enabled"),
    app: Optional[str] = Query(None, description="User has app (name contains, case-insensitive)"),
    limit: int = Query(100, ge=1, le=2000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> List[Dict[str, Any]]:
    """
    List users with optional filters:
      - status
      - mfa_enabled
      - app name substring
    """
    q = db.query(User)
    if status:
        q = q.filter(User.status == status)
    if mfa is not None:
        q = q.filter(User.mfa_enabled == mfa)
    if app:
        # Filter by users linked to apps matching the name substring
        ua_sub = (
            db.query(UserApp.user_id)
            .join(App, App.name == UserApp.app_name)
            .filter(func.lower(UserApp.app_name).like(f"%{app.lower()}%"))
            .subquery()
        )
        q = q.filter(User.user_id.in_(ua_sub))
    q = q.offset(offset).limit(limit)
    return [_user_to_dict(u, db) for u in q.all()]

@router.get("/devices")
def list_devices(
    status: Optional[str] = Query(None, description="Exact device status match"),
    location: Optional[str] = Query(None, description="Location contains, case-insensitive"),
    limit: int = Query(100, ge=1, le=2000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> List[Dict[str, Any]]:
    """List devices with optional filters on status and location."""
    q = db.query(Device)
    if status:
        q = q.filter(Device.status == status)
    if location:
        q = q.filter(func.lower(Device.location).like(f"%{location.lower()}%"))
    q = q.offset(offset).limit(limit)
    return [_device_to_dict(d, db) for d in q.all()]

@router.get("/apps")
def list_apps(
    q: Optional[str] = Query(None, description="Name contains, case-insensitive"),
    limit: int = Query(100, ge=1, le=2000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> List[Dict[str, Any]]:
    """List apps by optional name substring."""
    qq = db.query(App)
    if q:
        qq = qq.filter(func.lower(App.name).like(f"%{q.lower()}%"))
    qq = qq.offset(offset).limit(limit)
    return [_app_to_dict(a, db) for a in qq.all()]

# -------------------------------------------------------------------
# Unified CI lookup
# -------------------------------------------------------------------
@router.get("/ci/{ci_id}")
def get_ci(
    ci_id: str,
    kind: Optional[str] = Query(
        None,
        pattern="^(user|device|app)$",
        description="Restrict search to a specific type if desired",
    ),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Fetch a single Configuration Item (CI) by ID.

    - If `kind` is specified, look only in that table.
    - If not, auto-detect in order: device_id → user_id → app name → app_id.
    """
    if kind == "device":
        d = db.query(Device).filter(Device.device_id == ci_id).first()
        if not d: raise HTTPException(404, "Device not found")
        return {"kind": "device", "item": _device_to_dict(d, db)}

    if kind == "user":
        u = db.query(User).filter(User.user_id == ci_id).first()
        if not u: raise HTTPException(404, "User not found")
        return {"kind": "user", "item": _user_to_dict(u, db)}

    if kind == "app":
        a = db.query(App).filter(App.name == ci_id).first()
        if not a:
            # If name fails, try integer app_id
            try:
                aid = int(ci_id)
                a = db.query(App).filter(App.app_id == aid).first()
            except ValueError:
                a = None
        if not a: raise HTTPException(404, "App not found")
        return {"kind": "app", "item": _app_to_dict(a, db)}

    # Auto-detect search order
    d = db.query(Device).filter(Device.device_id == ci_id).first()
    if d: return {"kind": "device", "item": _device_to_dict(d, db)}

    u = db.query(User).filter(User.user_id == ci_id).first()
    if u: return {"kind": "user", "item": _user_to_dict(u, db)}

    a = db.query(App).filter(App.name == ci_id).first()
    if a: return {"kind": "app", "item": _app_to_dict(a, db)}

    # Final attempt: numeric app_id
    try:
        aid = int(ci_id)
        a2 = db.query(App).filter(App.app_id == aid).first()
        if a2: return {"kind": "app", "item": _app_to_dict(a2, db)}
    except ValueError:
        pass

    raise HTTPException(404, "CI not found")

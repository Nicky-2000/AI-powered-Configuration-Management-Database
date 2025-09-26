from copy import deepcopy
from datetime import datetime, timezone
import re
from typing import Optional
from .base import Normalizer
from .types import CITypes, Record

class RuleNormalizer(Normalizer):
    """
    Simple rule-based normalizer:
    takes a raw record (user or device) and
    standardizes fields so the database stays consistent.
    """
    def normalize_record(self, kind: CITypes, rec: Record) -> Record:
        r = deepcopy(rec)  # work on a copy so we don’t mutate the input
        if kind == "device":
            r["os"] = norm_os(r.get("os"))
            r["status"] = norm_status(r.get("status"))
            r["encryption"] = norm_bool_from_phrase(r.get("encryption_status"))
            r["assigned_user"] = clean_name(r.get("assigned_to"))
            r["last_checkin"] = parse_dt(r.get("last_checkin"))
        elif kind == "user":
            r["status"] = norm_status(r.get("status"))
            r["name"] = clean_name(r.get("name"))
            r["last_login"] = parse_dt(r.get("last_login"))
            if r.get("email"):
                r["email"] = r["email"].strip().lower()
        return r


# --- Individual field helpers (rule-based string cleanups) ---

def norm_status(s: Optional[str]):
    """Lower-case the status string if present."""
    return s.lower() if isinstance(s, str) else s

def norm_os(s: Optional[str]):
    """Map messy OS names to a few canonical labels."""
    if not s: return s
    x = s.strip().lower()
    if x.startswith("windows 10"): return "Windows 10"
    if x.startswith("windows 11"): return "Windows 11"
    if x in {"macos", "mac os", "osx", "mac os x"}: return "macOS"
    return s

def norm_bool_from_phrase(s: Optional[str]):
    """Convert free-form yes/no strings into True/False/None."""
    if s is None: return None
    t = str(s).strip().lower()
    if t in {"true","yes","y","1","enabled","on"}: return True
    if t in {"false","no","n","0","disabled","off"}: return False
    if "enabled" in t: return True   # fallback for phrases like "encryption enabled"
    return None

def parse_dt(z: Optional[str]):
    """Parse ISO-ish datetime strings into naive UTC datetime objects."""
    if not z:
        return None
    try:
        dt = datetime.fromisoformat(z.replace("Z", "+00:00"))
        if dt.tzinfo is not None:
            dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
        return dt
    except Exception:
        return None

def clean_name(n: Optional[str]):
    """Trim, collapse whitespace, and Title-case a name."""
    if not n: return n
    return re.sub(r"\s+", " ", n.strip()).title()

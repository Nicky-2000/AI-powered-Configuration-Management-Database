# app/nl/types.py
from typing import Literal, Optional, Dict, Any
from pydantic import BaseModel

Entity = Literal["users", "devices", "apps"]
Op     = Literal["list", "count"]

class Intent(BaseModel):
    entity: Entity          # target table
    op: Op = "list"         # list | count
    filters: Dict[str, Any] = {}  # normalized filters (mfa=False, app="Slack", status="active", etc.)
    limit: int = 100
    order_by: Optional[str] = None     # e.g., "last_checkin desc"

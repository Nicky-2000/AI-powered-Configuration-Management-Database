from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey
from .db import Base

# -----------------------------
# ORM models (tables) for the CMDB
# -----------------------------
class User(Base):
    __tablename__ = "users"
    # Represents an Okta-style user record
    user_id    = Column(String, primary_key=True)           # unique user ID
    name       = Column(String, nullable=False)
    email      = Column(String, unique=True, index=True, nullable=False)
    mfa_enabled= Column(Boolean)                            # MFA on/off
    last_login = Column(DateTime(timezone=True))
    status     = Column(String)                              # active/inactive
    groups     = Column(String)                              # comma-separated groups


class App(Base):
    __tablename__ = "apps"
    # Represents an application a user can access
    app_id = Column(Integer, primary_key=True, autoincrement=True)
    name   = Column(String, unique=True, index=True, nullable=False)
    owner  = Column(String)                                   # optional owner info
    type   = Column(String)                                   # e.g. "saas" or "onprem"


class UserApp(Base):
    __tablename__ = "user_apps"
    # Link table for many-to-many User <-> App relationships
    user_id  = Column(String, ForeignKey("users.user_id"), primary_key=True)
    app_name = Column(String, ForeignKey("apps.name"), primary_key=True)


class Device(Base):
    __tablename__ = "devices"
    # Represents a physical or virtual device in the CMDB
    device_id    = Column(String, primary_key=True)          # asset tag or ID
    hostname     = Column(String, index=True, nullable=False)
    ip_address   = Column(String)
    os           = Column(String)                             # normalized OS name
    assigned_user= Column(String)                             # linked user_id (string)
    location     = Column(String)
    encryption   = Column(Boolean)                            # True/False/NULL
    status       = Column(String)                             # e.g. active/retired
    last_checkin = Column(DateTime(timezone=True))

    # String representations for debugging/printing
    def __repr__(self):
        return f"<Device(device_id={self.device_id}, hostname={self.hostname}, os={self.os})>"

    def __str__(self):
        return (
            f"Device {self.device_id} ({self.hostname}, OS={self.os}), "
            f"assigned to {self.assigned_user}, status={self.status}, "
            f"last_checkin={self.last_checkin}, location={self.location}, "
            f"encryption={self.encryption}, ip={self.ip_address}"
        )

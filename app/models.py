from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey
from .db import Base

class User(Base):
    __tablename__ = "users"
    user_id = Column(String, primary_key=True)          # e.g., Okta user_id
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    mfa_enabled = Column(Boolean)
    last_login = Column(DateTime(timezone=True))
    status = Column(String)                             # 'active', 'inactive', etc.
    groups = Column(String)                             # comma-joined for prototype

class App(Base):
    __tablename__ = "apps"
    app_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, unique=True, index=True, nullable=False)
    owner = Column(String, nullable=True)               # optional metadata
    type = Column(String, nullable=True)                # 'saas' or 'onprem' (not enforced here)

class UserApp(Base):
    __tablename__ = "user_apps"
    user_id = Column(String, ForeignKey("users.user_id"), primary_key=True)
    app_name = Column(String, ForeignKey("apps.name"), primary_key=True)

class Device(Base):
    __tablename__ = "devices"
    device_id = Column(String, primary_key=True)        # e.g., asset tag
    hostname = Column(String, index=True, nullable=False)
    ip_address = Column(String)
    os = Column(String)                                 # normalized OS name
    assigned_user = Column(String)                      # display name or email (simple demo)
    location = Column(String)
    encryption = Column(Boolean)                        # True/False/NULL
    status = Column(String)                             # 'active', 'retired', etc.
    last_checkin = Column(DateTime(timezone=True))
    
    def __repr__(self):
        return f"<Device(device_id={self.device_id}, hostname={self.hostname}, os={self.os})>"
    def __str__(self):
        return f"Device {self.device_id} ({self.hostname}, OS={self.os}), assigned to {self.assigned_user}, status={self.status}, last_checkin={self.last_checkin}, location={self.location}, encryption={self.encryption}, ip={self.ip_address}"

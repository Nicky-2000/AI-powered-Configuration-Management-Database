# tests/conftest.py
import os
import tempfile
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.db import Base, get_db
from app.models import User, Device, App, UserApp


# --- Temporary SQLite DB file for the whole test session ---
@pytest.fixture(scope="session")
def tmp_db_url():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    url = f"sqlite:///{path}"
    yield url
    try:
        os.remove(path)
    except Exception:
        pass


@pytest.fixture(scope="session")
def engine(tmp_db_url):
    eng = create_engine(tmp_db_url, connect_args={"check_same_thread": False}, future=True)
    Base.metadata.create_all(bind=eng)
    return eng


@pytest.fixture(scope="function")
def db_session(engine):
    TestingSession = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)
    db = TestingSession()
    try:
        yield db
    finally:
        db.rollback()
        db.close()


# --- Override FastAPI's DB dependency to use our test session ---
@pytest.fixture(autouse=True)
def override_get_db(db_session):
    def _get_db():
        try:
            yield db_session
        finally:
            pass
    app.dependency_overrides[get_db] = _get_db
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


# --- Utility: clear tables in FK-safe order (and reset autoincrement) ---
def _clear_all(db):
    # child → parent order
    db.execute(text("DELETE FROM user_apps"))
    db.execute(text("DELETE FROM devices"))
    db.execute(text("DELETE FROM users"))
    db.execute(text("DELETE FROM apps"))
    # reset autoincrement for SQLite (optional but nice for predictability)
    try:
        db.execute(text("DELETE FROM sqlite_sequence WHERE name IN ('apps')"))
    except Exception:
        # not critical if sqlite_sequence doesn't exist
        pass
    db.commit()


# --- The seed fixture you wanted ---
@pytest.fixture
def seed_sample(db_session):
    """
    Seeds a consistent, conflict-free dataset that matches your models:
      - apps.app_id is AUTOINCREMENT → we DO NOT set it manually
      - UserApp references users.user_id and apps.name
      - devices.assigned_user stores the user_id string in your model
    """
    _clear_all(db_session)

    # 1) Users (emails are unique)
    users = [
        User(user_id="U001", name="Alice Adams", email="alice@example.com",
             mfa_enabled=True, status="active", groups="staff"),
        User(user_id="U002", name="Bob", email="bob@example.com",
             mfa_enabled=False, status="active", groups="staff"),
        User(user_id="U003", name="Adam Smith", email="adam@example.com",
             mfa_enabled=False, status="inactive", groups=None),
    ]
    db_session.add_all(users)
    db_session.commit()

    # 2) Apps (DO NOT set app_id; let SQLite assign it)
    apps = [
        App(name="Slack", owner="IT", type="chat"),
        App(name="Okta",  owner="Sec", type="idp"),
    ]
    db_session.add_all(apps)
    db_session.commit()

    # 3) User ↔ App links (FK to users.user_id and apps.name)
    links = [
        UserApp(user_id="U001", app_name="Slack"),
        UserApp(user_id="U002", app_name="Slack"),
        UserApp(user_id="U001", app_name="Okta"),
    ]
    db_session.add_all(links)
    db_session.commit()

    # 4) Devices (your model stores assigned_user as a plain string; we use user_id)
    devices = [
        Device(device_id="D001", hostname="host1", os="macOS",
               assigned_user="U001", location="NY", encryption=True, status="active"),
        Device(device_id="D002", hostname="host2", os="linux",
               assigned_user="U002", location="SF", encryption=False, status="active"),
    ]
    db_session.add_all(devices)
    db_session.commit()

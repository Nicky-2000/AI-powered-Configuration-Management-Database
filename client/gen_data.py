# client/data_gen.py
import random
from datetime import datetime, timedelta, timezone

FIRST = ["Alex","Jamie","Taylor","Jordan","Sam","Avery","Casey","Riley","Morgan","Quinn","Jesse","Cameron"]
LAST  = ["Chen","Garcia","Patel","Santos","Lee","Kim","Johnson","Brown","Wilson","Martinez","Davis","Nguyen"]
CITIES= ["New York HQ","SF","London","Berlin","Tokyo","Toronto","Sydney","Dublin","Paris"]
OS    = ["macos","Windows 10 Pro","Windows 11 Pro","Ubuntu 22.04"]
APPS  = ["Slack","GitHub","Salesforce","Jira","Notion","Zoom","Workday","Okta","Datadog"]

def _name(): return f"{random.choice(FIRST)} {random.choice(LAST)}"
def _email(n): return f"{''.join(c for c in n.lower() if c.isalpha())}@example.com"
def _ip(): return f"10.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}"
def _dev_id(): return f"C-{random.randint(10000,99999)}"
def _host(n): return f"{n.split()[0].lower()}-mbp-{random.randint(100,999)}"
def _iso_ago(days=0, jitter_h=0):
    dt = datetime.now(timezone.utc) - timedelta(days=days, hours=random.randint(0, jitter_h))
    return dt.isoformat()

def gen_hardware_record():
    n = _name()
    return {
        "device_id": _dev_id(),
        "hostname": _host(n),
        "assigned_to": n,
        "os": random.choice(OS),
        "ip_address": _ip(),
        "last_checkin": _iso_ago(days=random.randint(0,90), jitter_h=18),
        "location": random.choice(CITIES),
        "encryption_status": random.choice(["FileVault Enabled","BitLocker Enabled","disabled"]),
        "status": random.choice(["active","active","active","retired"]),
    }

def gen_okta_user_record():
    n = _name()
    return {
        "user_id": f"u_{random.randint(100,99999)}",
        "name": n,
        "email": _email(n),
        "groups": random.sample(["Engineering","Admins","HR","Finance","IT","Sales"], k=random.randint(1,2)),
        "apps": random.sample(APPS, k=random.randint(1,4)),
        "mfa_enabled": random.choice([True, True, False]),
        "last_login": _iso_ago(days=random.randint(0,60), jitter_h=12),
        "status": "ACTIVE",
    }

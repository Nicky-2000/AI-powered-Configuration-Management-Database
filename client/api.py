import os, requests
from dotenv import load_dotenv
load_dotenv()
API = os.getenv("API_BASE_URL", "http://localhost:8000")
S = requests.Session(); S.headers.update({"Content-Type":"application/json"})

def healthz():   r=S.get(f"{API}/healthz",timeout=10); r.raise_for_status(); return r.json()
def ingest(b):   r=S.post(f"{API}/ingest",json=b,timeout=60); r.raise_for_status(); return r.json()
def users(**p):  r=S.get(f"{API}/users", params=p,timeout=30); r.raise_for_status(); return r.json()
def devices(**p):r=S.get(f"{API}/devices",params=p,timeout=30); r.raise_for_status(); return r.json()
def ci(ci_id: str, kind: str | None = None):
    params = {}
    if kind:
        params["kind"] = kind
    r = requests.get(f"{API}/ci/{ci_id}", params=params, timeout=20)
    r.raise_for_status()
    return r.json()

def apps(**p):   r=S.get(f"{API}/apps",   params=p,timeout=30); r.raise_for_status(); return r.json()
def ask(q,limit=100):
    r=S.post(f"{API}/ask",json={"q":q,"limit":int(limit)},timeout=90); r.raise_for_status(); return r.json()



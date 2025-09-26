def test_ingest_then_read_user(client):
    payload = [
            {
                "user_id": "u_235",
                "name": "Carlos S.",
                "email": "c.santos@example.com",
                "groups": ["HR"],
                "apps": ["Workday"],
                "mfa_enabled": "False",
                "last_login": "2024-06-21T08:41:00Z",
                "status": "ACTIVE",
            },
        ]
    r = client.post("/ingest", json=payload)
    assert r.status_code == 200
    r2 = client.get("/users")
    assert r2.status_code == 200
    assert any(u["user_id"] == "u_235" for u in r2.json())

def test_ingest_overwrite(client):
    payload = [
            {
                "user_id": "u_235",
                "name": "Carlos S.",
                "email": "c.santos@example.com",
                "groups": ["HR"],
                "apps": ["Workday"],
                "mfa_enabled": "True",
                "last_login": "2024-06-21T08:41:00Z",
                "status": "ACTIVE",
            },
        ]
    r = client.post("/ingest", json=payload)
    assert r.status_code == 200
    # Confirm the change took effect
    r = client.get("/ci/u_235")
    assert r.status_code == 200
    p = r.json()
    assert p['item']["mfa_enabled"] == True

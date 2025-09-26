def test_list_users(client, seed_sample):
    r = client.get("/users")
    assert r.status_code == 200
    data = r.json()
    assert any(u["user_id"] == "U001" for u in data)

def test_list_devices(client, seed_sample):
    r = client.get("/devices")
    assert r.status_code == 200
    data = r.json()
    assert any(d["device_id"] == "D001" for d in data)

def test_list_apps(client, seed_sample):
    r = client.get("/apps")
    assert r.status_code == 200
    data = r.json()
    assert any(a["name"] == "Slack" for a in data)

def test_get_ci_user(client, seed_sample):
    r = client.get("/ci/U001")
    assert r.status_code == 200
    p = r.json()
    assert p["kind"] == "user"
    assert p["item"]["user_id"] == "U001"

def test_get_ci_device(client, seed_sample):
    r = client.get("/ci/D001")
    assert r.status_code == 200
    assert r.json()["kind"] == "device"

def test_get_ci_app_by_name(client, seed_sample):
    r = client.get("/ci/Slack")
    assert r.status_code == 200
    assert r.json()["kind"] == "app"

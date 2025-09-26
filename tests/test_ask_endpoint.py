def test_ask_contains_name(client, seed_sample, monkeypatch):
    # Mock model output → deterministic SQL
    from app.nl import naturalsql_local
    monkeypatch.setattr(
        naturalsql_local, "generate_sql",
        lambda q, limit=100: "SELECT user_id, name FROM users WHERE name LIKE '%Adam%' LIMIT 100"
    )
    r = client.post("/ask", json={"q": "Which users have Adam in their name?", "limit": 100})
    assert r.status_code == 200
    out = r.json()
    assert out["ok"] is True
    assert out["sql"].lower().startswith("select")
    assert any("Adam" in row["name"] for row in out["rows"])

def test_ask_count_aggregate(client, seed_sample, monkeypatch):
    from app.nl import naturalsql_local

    # Deterministic SQL with an alias
    monkeypatch.setattr(
        naturalsql_local,
        "generate_sql",
        lambda q, limit=100: "SELECT COUNT(*) AS count FROM users WHERE LOWER(name) LIKE '%a%'"
    )

    r = client.post("/ask", json={"q": "How many users contain 'a'?"})
    assert r.status_code == 200, r.text

    out = r.json()
    assert out["ok"] is True

    sql_text = str(out["sql"]).upper()
    assert "COUNT" in sql_text, f"unexpected SQL: {out['sql']}"

    # Must have at least one row
    assert out.get("rows") is not None, f"missing rows in response: {out}"
    assert len(out["rows"]) >= 1, f"empty rows; sql={out['sql']}"

    row0 = out["rows"][0]

    # Accept either 'count' alias or any single aggregate key
    if "count" in row0:
        val = row0["count"]
    else:
        # fallback: support engines returning 'COUNT(*)' etc.
        k = next(iter(row0.keys()))
        val = row0[k]

    assert isinstance(val, int), f"expected int, got {type(val)} with row {row0}"
    assert val >= 1, f"expected >=1, got {val}; rows={out['rows']}, sql={out['sql']}"

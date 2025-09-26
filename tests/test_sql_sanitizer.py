from app.nl.naturalsql_local import sanitize_sql

def test_sanitize_only_select():
    s = sanitize_sql("SELECT * FROM users", limit=10)
    assert s.ok and "SELECT" in s.sql

    bad = sanitize_sql("DROP TABLE users;", limit=10)
    assert not bad.ok
    assert "only select" in bad.reason.lower()

def test_sanitize_force_limit():
    s = sanitize_sql("SELECT * FROM users", limit=7)
    assert s.ok
    assert "limit 7" in s.sql.lower()

def test_sanitize_allowlisted_tables():
    # references a non-allowlisted table
    bad = sanitize_sql("SELECT * FROM secrets", limit=10)
    assert not bad.ok
    assert "allowlisted" in bad.reason.lower()

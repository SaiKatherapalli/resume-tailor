"""API basics: health check and tables."""

from sqlalchemy import inspect


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_tables_are_created(client):
    tables = inspect(client.app.state.engine).get_table_names()
    assert set(tables) == {"users", "career_banks", "tailor_jobs"}


def test_request_id_header(client):
    assert len(client.get("/health").headers["X-Request-ID"]) == 12
    assert client.get("/health", headers={"X-Request-ID": "abc"}).headers["X-Request-ID"] == "abc"
    fake = client.get("/health", headers={"X-Request-ID": "x	FAKE LOG LINE"}).headers["X-Request-ID"]
    assert "FAKE" not in fake


def test_login_rate_limit(client):
    client.app.state.login_limiter.limit = 3
    form = {"username": "x@example.com", "password": "wrong-pass"}
    codes = [client.post("/auth/login", data=form).status_code for _ in range(4)]
    assert codes == [401, 401, 401, 429]


def test_rate_limiter_forgets_old_hits():
    from api.middleware import RateLimiter

    limiter = RateLimiter(limit=1, window=0)  # window 0: every hit is already "old"
    limiter.check("ip")
    limiter.check("ip")  # no error

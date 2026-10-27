from api.security import create_access_token, read_access_token


def test_register_login_me(client, auth):
    me = client.get("/auth/me", headers=auth)
    assert me.status_code == 200
    assert me.json()["email"] == "sai@example.com"
    assert "password_hash" not in me.json()


def test_email_is_normalized_and_unique(client):
    first = client.post("/auth/register", json={"email": " Sai@Example.com", "password": "12345678"})
    assert first.json()["email"] == "sai@example.com"
    again = client.post("/auth/register", json={"email": "sai@example.com", "password": "12345678"})
    assert again.status_code == 409


def test_bad_input_is_rejected(client):
    assert (
        client.post("/auth/register", json={"email": "not-an-email", "password": "12345678"}).status_code
        == 422
    )
    assert client.post("/auth/register", json={"email": "a@b.com", "password": "short"}).status_code == 422


def test_wrong_password(client, auth):
    r = client.post("/auth/login", data={"username": "sai@example.com", "password": "wrong-pass"})
    assert r.status_code == 401
    r = client.post("/auth/login", data={"username": "nobody@example.com", "password": "wrong-pass"})
    assert r.status_code == 401  # same answer, so attackers can't tell which emails exist


def test_no_token_or_fake_token(client):
    assert client.get("/auth/me").status_code == 401
    assert client.get("/auth/me", headers={"Authorization": "Bearer fake.token.here"}).status_code == 401


def test_token_round_trip():
    assert read_access_token(create_access_token("user123")) == "user123"
    assert read_access_token("garbage") is None

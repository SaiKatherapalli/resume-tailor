"""Shared test fixtures. pytest loads this file automatically."""

import pytest
from fastapi.testclient import TestClient

from api.main import create_app


@pytest.fixture
def client(tmp_path):
    """An API client with a fresh, empty SQLite database for each test."""
    app = create_app(f"sqlite:///{tmp_path / 'test.db'}")
    with TestClient(app) as c:  # "with" runs startup (creates tables) and shutdown
        yield c


def register_and_login(client, email="sai@example.com", password="secret-pass-123") -> dict:
    """Create a user and return the headers to call the API as that user."""
    client.post("/auth/register", json={"email": email, "password": password})
    token = client.post("/auth/login", data={"username": email, "password": password}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def auth(client):
    return register_and_login(client)

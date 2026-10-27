"""API tests. Each test gets a fresh SQLite file in a temp folder."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import inspect

from api.main import create_app


@pytest.fixture
def client(tmp_path):
    app = create_app(f"sqlite:///{tmp_path / 'test.db'}")
    with TestClient(app) as c:  # "with" runs startup (creates tables) and shutdown
        yield c


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_tables_are_created(client):
    tables = inspect(client.app.state.engine).get_table_names()
    assert set(tables) == {"users", "career_banks", "tailor_jobs"}

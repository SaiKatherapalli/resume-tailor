"""API basics: health check and tables."""

from sqlalchemy import inspect


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_tables_are_created(client):
    tables = inspect(client.app.state.engine).get_table_names()
    assert set(tables) == {"users", "career_banks", "tailor_jobs"}

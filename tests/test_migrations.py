"""The migration files must build exactly the tables in api/models.py."""

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

from core.config import PROJECT_ROOT


def test_migrations_match_models(tmp_path):
    url = f"sqlite:///{tmp_path / 'm.db'}"
    cfg = Config(str(PROJECT_ROOT / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", url)

    command.upgrade(cfg, "head")
    tables = set(inspect(create_engine(url)).get_table_names())
    assert {"users", "career_banks", "tailor_jobs"} <= tables

    command.check(cfg)  # fails if models.py changed but no migration was written
    command.downgrade(cfg, "base")  # and we can undo it

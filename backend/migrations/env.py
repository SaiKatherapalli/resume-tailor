"""Alembic runs this file for every migration command."""

from logging.config import fileConfig

from alembic import context

from api import models  # noqa: F401  (registers the tables on Base)
from api.db import Base, make_engine
from core.config import get_settings

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Our tables. --autogenerate compares these with the real database.
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Only print the SQL (alembic upgrade head --sql), don't connect."""
    context.configure(url=get_settings().database_url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    url = config.get_main_option("sqlalchemy.url") or get_settings().database_url  # tests can override
    with make_engine(url).connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=connection.dialect.name == "sqlite",  # SQLite can't ALTER tables directly
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

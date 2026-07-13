from logging.config import fileConfig

from sqlalchemy import create_engine, pool
from alembic import context

# ── Load app settings and models ─────────────────────────────────────────────
from app.config import settings
from app.database import Base
import app.models  # noqa: F401 — ensures all models are registered on Base.metadata

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# Use settings.database_url directly — bypasses ConfigParser interpolation
# which chokes on special characters like % in the password.
DB_URL = settings.database_url


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (no live DB connection needed)."""
    context.configure(
        url=DB_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode (connects to the DB)."""
    connectable = create_engine(DB_URL, poolclass=pool.NullPool)

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

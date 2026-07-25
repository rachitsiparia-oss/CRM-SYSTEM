from logging.config import fileConfig

from alembic import context
from app.core.config import get_settings
from app.db.base import Base

# Import every model module so its table is registered on Base.metadata —
# required for autogenerate to see it. New models get a line here.
from app.db.models import audit_event, job_record, outbox_event  # noqa: F401
from sqlalchemy import engine_from_config, pool

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# DATABASE_URL comes from our own validated Settings, not a duplicated
# alembic.ini value — one source of configuration truth
# (DEPLOYMENT_AND_ENV.md section 4.1).
settings = get_settings()
if settings.database_url:
    config.set_main_option("sqlalchemy.url", settings.database_url)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Emit SQL without a live connection — used to review a migration's
    generated SQL before applying it."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

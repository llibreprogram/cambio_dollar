from __future__ import annotations

from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import engine_from_config, pool

# Interpret the config file for Python logging.
if context.config.config_file_name is not None:
    fileConfig(context.config.config_file_name)


def _ensure_sqlalchemy_url() -> None:
    config = context.config
    existing = config.get_main_option("sqlalchemy.url")
    if existing:
        return
    from cambio_dollar.config import get_settings

    settings = get_settings()
    db_path = Path(settings.db_path).expanduser().resolve()
    config.set_main_option("sqlalchemy.url", f"sqlite+pysqlite:///{db_path}")


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""

    _ensure_sqlalchemy_url()
    config = context.config
    url = config.get_main_option("sqlalchemy.url")
    if not url:
        raise RuntimeError("No se pudo determinar la URL de la base de datos para migraciones offline.")

    context.configure(url=url, target_metadata=None, literal_binds=True)

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""

    _ensure_sqlalchemy_url()
    config = context.config
    connectable = engine_from_config(
        config.get_section(config.config_ini_section) or {},
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=None)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

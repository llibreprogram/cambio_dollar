# Copyright (c) 2025 Cambio Dollar Project
# All rights reserved.
#
# This software is licensed under the MIT License.
# See LICENSE file for more details.

from __future__ import annotations

import argparse
import logging
import sqlite3
from pathlib import Path
from typing import Optional

from alembic import command
from alembic.config import Config

LOGGER = logging.getLogger(__name__)

BASELINE_REVISION = "0001_initial_schema"


def _default_db_path() -> Path:
    from .config import get_settings

    settings = get_settings()
    return Path(settings.db_path)


def _build_config(db_path: Path) -> Config:
    cfg = Config()
    migrations_path = Path(__file__).resolve().parent / "migrations"
    cfg.set_main_option("script_location", str(migrations_path))
    cfg.set_main_option("sqlalchemy.url", f"sqlite+pysqlite:///{db_path}")
    cfg.attributes["configure_logger"] = False
    return cfg


def upgrade_database(db_path: Optional[Path] = None) -> None:
    path = Path(db_path or _default_db_path()).expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    config = _build_config(path)
    needs_baseline_stamp = False

    if path.exists():
        with sqlite3.connect(path) as conn:
            has_version = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='alembic_version'"
            ).fetchone()
            if not has_version:
                existing_tables = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
                ).fetchall()
                if existing_tables:
                    needs_baseline_stamp = True

    LOGGER.debug("Ejecutando migraciones Alembic en %s", path)
    if needs_baseline_stamp:
        LOGGER.info(
            "Base existente detectada sin versiones Alembic; registrando migración base %s.",
            BASELINE_REVISION,
        )
        command.stamp(config, BASELINE_REVISION)
    command.upgrade(config, "head")


def create_revision(message: str, *, autogenerate: bool = False, db_path: Optional[Path] = None) -> None:
    path = Path(db_path or _default_db_path()).expanduser().resolve()
    config = _build_config(path)
    LOGGER.info("Creando nueva migración Alembic: %s", message)
    command.revision(config, message=message, autogenerate=autogenerate)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Herramientas para migraciones de Cambio Dollar")
    parser.add_argument(
        "--db",
        type=str,
        default=None,
        help="Ruta al archivo SQLite (por defecto toma CAMBIO_DB_PATH de la configuración).",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("upgrade", help="Aplica todas las migraciones pendientes (hasta head)")

    revision_parser = sub.add_parser("revision", help="Crea una nueva migración vacía")
    revision_parser.add_argument("message", type=str, help="Mensaje descriptivo de la migración")
    revision_parser.add_argument(
        "--autogenerate",
        action="store_true",
        help="Habilita autogeneración basada en metadatos SQLAlchemy",
    )

    return parser


def main(argv: Optional[list[str]] = None) -> None:
    parser = _build_parser()
    args = parser.parse_args(argv)
    db = Path(args.db).expanduser() if args.db else None

    if args.command == "upgrade":
        upgrade_database(db)
    elif args.command == "revision":
        create_revision(args.message, autogenerate=args.autogenerate, db_path=db)
    else:  # pragma: no cover - debería ser imposible por argparse
        parser.error(f"Comando no soportado: {args.command}")


if __name__ == "__main__":  # pragma: no cover - CLI manual
    main()

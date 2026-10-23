"""Small admin CLI: ``python -m app.cli <command>``.

Commands
    init-db   apply migrations then seed the built-in robots (idempotent)
    migrate   apply migrations only
    seed      seed built-in robots only
    reset     delete the SQLite file and rebuild it (asks unless --yes)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]


def _run_migrations() -> None:
    from alembic import command
    from alembic.config import Config

    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    command.upgrade(cfg, "head")


def _seed() -> int:
    from app.core.config import get_settings
    from app.core.db import create_db_engine, create_session_factory
    from app.seeds import seed_characters

    settings = get_settings()
    engine = create_db_engine(settings.database_url)
    factory = create_session_factory(engine)
    with factory() as session:
        return seed_characters(session)


def _ensure_dirs() -> None:
    from app.core.config import get_settings

    settings = get_settings()
    settings.storage_dir.mkdir(parents=True, exist_ok=True)
    settings.audio_storage_dir.mkdir(parents=True, exist_ok=True)
    settings.tts_voices_dir.mkdir(parents=True, exist_ok=True)


def cmd_init_db() -> int:
    _ensure_dirs()
    _run_migrations()
    count = _seed()
    from app.core.config import get_settings

    settings = get_settings()
    print(f"Database ready: {settings.database_url}")
    print(f"Seeded {count} built-in characters.")
    return 0


def cmd_migrate() -> int:
    _ensure_dirs()
    _run_migrations()
    print("Migrations applied.")
    return 0


def cmd_seed() -> int:
    count = _seed()
    print(f"Seeded {count} built-in characters.")
    return 0


def cmd_reset(yes: bool) -> int:
    from app.core.config import get_settings

    settings = get_settings()
    db_file = settings.sqlite_file
    if db_file is None:
        print("Refusing to reset a non-file database.", file=sys.stderr)
        return 1
    if not yes:
        answer = input(f"Delete {db_file} and rebuild? [y/N] ").strip().lower()
        if answer not in {"y", "yes"}:
            print("Aborted.")
            return 1
    for suffix in ("", "-wal", "-shm"):
        candidate = Path(str(db_file) + suffix)
        if candidate.exists():
            candidate.unlink()
    return cmd_init_db()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="app.cli")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("init-db", help="apply migrations and seed built-ins")
    sub.add_parser("migrate", help="apply migrations only")
    sub.add_parser("seed", help="seed built-ins only")
    reset = sub.add_parser("reset", help="delete and rebuild the database")
    reset.add_argument("--yes", action="store_true")

    args = parser.parse_args(argv)
    if args.command == "init-db":
        return cmd_init_db()
    if args.command == "migrate":
        return cmd_migrate()
    if args.command == "seed":
        return cmd_seed()
    if args.command == "reset":
        return cmd_reset(args.yes)
    parser.error("unknown command")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
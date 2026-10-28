"""Apply ordered SQL migrations to a PostgreSQL database."""

from __future__ import annotations

import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
MIGRATIONS = ROOT / "migrations"


def migrate(database_url: str) -> tuple[str, ...]:
    try:
        import psycopg
    except ImportError as exc:
        raise RuntimeError("install the optional 'postgres' dependency group") from exc

    applied: list[str] = []
    with psycopg.connect(database_url, autocommit=True) as connection:
        connection.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations "
            "(version TEXT PRIMARY KEY, applied_at TIMESTAMPTZ NOT NULL DEFAULT now())"
        )
        known = {row[0] for row in connection.execute("SELECT version FROM schema_migrations")}
        for path in sorted(MIGRATIONS.glob("*.sql")):
            if path.name in known:
                continue
            sql = path.read_text(encoding="utf-8")
            with connection.transaction():
                connection.execute(sql)
                connection.execute(
                    "INSERT INTO schema_migrations (version) VALUES (%s)", (path.name,)
                )
            applied.append(path.name)
    return tuple(applied)


def main() -> int:
    database_url = os.environ.get("DATABASE_URL", "").strip()
    if not database_url:
        print("DATABASE_URL is required", file=sys.stderr)
        return 2
    try:
        applied = migrate(database_url)
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"Database migration failed: {exc}", file=sys.stderr)
        return 1
    print("Applied: " + (", ".join(applied) if applied else "no pending migrations"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

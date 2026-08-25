from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Iterator

import psycopg
from psycopg.rows import dict_row

from app.core.config import settings


@contextmanager
def connection() -> Iterator[psycopg.Connection]:
    if not settings.database_url:
        raise RuntimeError("Set DATABASE_URL in .env (Supabase → Settings → Database).")
    with psycopg.connect(settings.database_url, row_factory=dict_row) as conn:
        yield conn


def fetch_one(sql: str, params: tuple[Any, ...] = ()) -> dict[str, Any] | None:
    with connection() as conn:
        row = conn.execute(sql, params).fetchone()
        return dict(row) if row else None


def fetch_all(sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    with connection() as conn:
        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]


def execute(sql: str, params: tuple[Any, ...] = ()) -> None:
    with connection() as conn:
        conn.execute(sql, params)
        conn.commit()


def ping() -> None:
    with connection() as conn:
        conn.execute("SELECT 1")

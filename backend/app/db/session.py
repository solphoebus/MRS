from __future__ import annotations

from functools import lru_cache

from app.core.config import get_settings
from app.db.sqlite_store import SQLiteStore


@lru_cache
def get_store() -> SQLiteStore:
    return SQLiteStore(get_settings().database_url)


def init_db() -> None:
    get_store()

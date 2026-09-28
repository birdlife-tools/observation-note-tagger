"""Base repository with shared database pool."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import asyncpg


class BaseRepository:
    """Base class for PostgreSQL repositories."""

    def __init__(self, db_pool: asyncpg.Pool):
        self.db = db_pool

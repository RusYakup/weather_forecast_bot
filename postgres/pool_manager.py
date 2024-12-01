import asyncpg
import traceback
from config.config import get_settings

import logging

log = logging.getLogger(__name__)


async def create_pool() -> asyncpg.pool.Pool:
    """
    Creates a connection pool to a PostgreSQL database.

    Returns:
        asyncpg.pool.Pool: The connection pool to the database.
    """
    try:
        settings = get_settings()
        dsn = f"postgresql://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@{settings.POOL_HOST_DB}/{settings.POSTGRES_DB}"
        pool = await asyncpg.create_pool(
            dsn=dsn,
            min_size=3,
            max_size=100,
            max_inactive_connection_lifetime=60,
            max_queries=1000,

        )
        log.info("Successfully connected to the database: %s", dsn)
        return pool
    except Exception as e:
        log.error("Failed to connect to the database: %s", str(e))
        log.error("Exception traceback:\n%s", traceback.format_exc())
        exit(1)

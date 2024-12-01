import logging
import functools

log = logging.getLogger(__name__)


def log_database_query(func):
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        log.debug(f"Query is being made to the database: {func.__name__}")
        result = await func(*args, **kwargs)
        log.debug(f"Database query completed: {func.__name__}")
        return result
    return wrapper

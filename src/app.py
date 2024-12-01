import traceback
import logging
import sys
import uvicorn
from config.config import get_settings
from helpers.helpers import logging_config, check_bot_token, check_api_key
from helpers.set_webhook import set_webhook
from postgres.database_adapters import create_table
from prometheus.couters import inc_counters
from postgres.pool import DbPool
from handlers.db_handlers import bd_router
from handlers.tg_handler import webhook_router
from prometheus_fastapi_instrumentator import Instrumentator
from fastapi import FastAPI
from contextlib import asynccontextmanager

log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for FastAPI application.

    This context manager creates a database connection pool when the application starts,
    and closes the pool when the application ends.

    If an unexpected error occurs while creating the pool, the application will exit with code 1.
    If an error occurs while closing the pool, the error will be logged.
    """
    try:
        settings = get_settings()
        logging_config(settings.LOG_LEVEL)
        await DbPool.create_pool()
        pool = await DbPool.get_pool()
        check_bot_token(settings.TOKEN)
        check_api_key(settings.API_KEY)
        set_webhook(settings.TOKEN, settings.APP_DOMAIN, settings.SECRET_TOKEN_TG_WEBHOOK)
        await create_table(pool)
        await inc_counters()
        log.info("Startup completed successfully")

        if not pool:
            log.error("Failed to create database connection pool")
            sys.exit(1)
        yield
    except Exception as e:
        log.error(f"An unexpected error occurred: {e}")
        sys.exit(1)
    finally:
        try:
            await DbPool.close_pool()
        except Exception as e:
            log.error(f"An error occurred while closing the database connection pool: {e}")


app = FastAPI(lifespan=lifespan)
app.include_router(bd_router)
app.include_router(webhook_router)

instrumental = Instrumentator().instrument(app).expose(app, include_in_schema=False, should_gzip=True)

if __name__ == "__main__":
    try:
        uvicorn.run(app, host="0.0.0.0", port=get_settings().LISTEN_PORT, log_level=get_settings().LOG_LEVEL_UVICORN)
    except Exception as e:
        log.error(f"error during start: {e}")
        log.debug(traceback.format_exc())
        sys.exit(1)

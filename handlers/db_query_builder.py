from postgres.decorators import log_database_query
from postgres.sqlfactory import SQLQueryBuilder
from postgres.database_adapters import execute_query
from asyncpg import Pool
import logging
import traceback

log = logging.getLogger(__name__)


@log_database_query
async def execute_users_actions(pool: Pool, chat_id: int = None, from_ts: int = None, until_ts: int = None,
                                limits: int = 1000):
    if pool is None:
        raise ValueError("Pool is None")

    conditions = {}
    if chat_id is not None:
        conditions["chat_id"] = ("=", chat_id)
    if from_ts is not None:
        conditions["ts"] = (">", from_ts)
    if until_ts is not None:
        conditions["ts"] = ("<", until_ts)
    try:
        builder = SQLQueryBuilder("statistic")
        builder.select().where(conditions).order_by("ts", "DESC").limit(limits)
    except Exception as e:
        log.error("execute_users_actions: An error occurred: %s", str(e))
        log.debug(f"execute_users_actions: Exception traceback: \n {traceback.format_exc()}")
        raise
    try:
        res = await execute_query(pool, builder.sql, *builder.args, fetch=True)
    except Exception as e:
        log.error("execute_users_actions:An error occurred: %s", str(e))
        log.debug(f"execute_users_actions: Exception traceback: \n {traceback.format_exc()}")
        raise

    return res


@log_database_query
async def execute_actions_count(pool: Pool, chat_id: int):
    """ SELECT chat_id, DATE_TRUNC('month', to_timestamp(ts)) AS month, COUNT(*) AS actions_count FROM statistic
    WHERE chat_id = $1 GROUP BY chat_id, month
    """
    try:
        fields_select = [
            "chat_id",
            "DATE_TRUNC('month', to_timestamp(ts)) AS month",
            "COUNT(*) AS actions_count"
        ]
        bilder = SQLQueryBuilder("statistic")
        bilder.select(fields_select).where({"chat_id": ("=", chat_id)}).group_by(["chat_id", "month"])
        res = await execute_query(pool, bilder.sql, *bilder.args, fetch=True)
        return res
    except Exception as e:
        log.error("An error occurred: %s", str(e))
        log.debug(f"Exception traceback:\n{traceback.format_exc()}")

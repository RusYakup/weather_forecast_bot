import asyncpg
import logging
import traceback
from fastapi.security import HTTPBasic
from postgres.decorators import log_database_query
from helpers.model_message import Message
from prometheus.couters import instance_id, database_errors_counters, count_instance_errors
from postgres.sqlfactory import SQLQueryBuilder
from asyncpg import Pool
from typing import Union, Optional, List

log = logging.getLogger(__name__)
security = HTTPBasic()


async def create_table(pool: Pool):
    """
    This function creates two tables: user_state and statistic.
    """
    log.debug("Creating table...")
    create_user_state_table = """
        CREATE TABLE IF NOT EXISTS user_state (
            chat_id INTEGER PRIMARY KEY,
            city VARCHAR(50),
            date_difference VARCHAR(15),
            qty_days VARCHAR(15),
            CONSTRAINT unique_chat_id UNIQUE (chat_id)
        );
    """
    create_statistic_table = """
        CREATE TABLE IF NOT EXISTS statistic (
            id SERIAL PRIMARY KEY,
            ts INTEGER,
            user_id INTEGER,
            user_name VARCHAR(50),
            chat_id INTEGER,
            action VARCHAR(50)
        );
    """
    create_users_online_table = """
    CREATE TABLE IF NOT EXISTS users_online (
            chat_id INTEGER NOT NULL UNIQUE,
            timestamp INTEGER NOT NULL
    );
    """

    try:
        async with pool.acquire() as connection:
            async with connection.transaction():
                await connection.execute(create_user_state_table)  # Execute user_state table creation
                await connection.execute(create_statistic_table)  # Execute statistic table creation
                await connection.execute(create_users_online_table)

        log.info("Tables created successfully")
    except Exception as e:
        log.error(f"An error occurred during table creation: {e}")
        log.debug("Exception traceback:", traceback.format_exc())
        exit(1)  # Exit the program with error code 1


@log_database_query
async def sql_update_user_state_bd(bot, pool: asyncpg.Pool, message, fields: str, new_state: str = "waiting_value"):
    """
    Update the user state in the database by setting the given fields to the new state.

    Args:
        bot: The asynchronous Telegram bot instance.
        pool (asyncpg.Pool): The connection pool to the database.
        message: The message object containing the necessary information.
        fields (str): The fields to be updated in the database.
        new_state (str): The new state of the fields. Defaults to "waiting_value".

    Raises:
        Exception: If an error occurs during the process.
    """
    try:
        # Build the query to update the user state
        conditions = {
            "chat_id": ("=", message.chat.id),
        }
        builder = SQLQueryBuilder("user_state")
        builder.update({fields: new_state}).where(conditions)
        # Execute the query and check the result
        await execute_query(pool, builder.sql, *builder.args, fetch=True)
        if new_state == "waiting_value":
            log.info(f"User {message.chat.id} state waiting_value for {fields}")
        else:
            log.info(f"User {message.chat.id} {fields} updated successfully")
    except Exception as e:
        count_instance_errors.labels(instance=instance_id).inc()
        await bot.send_message(message.chat.id, "An error occurred. Please try again later.")
        log.error(f"An error occurred during user state adding: {e}")
        log.debug("Exception traceback:", traceback.format_exc())


@log_database_query
async def add_statistic_bd(pool: asyncpg.Pool, message: Message) -> None:
    """
    Add a statistic record to the database based on the message received.

    Args:
        pool (asyncpg.Pool): The connection pool to the database.
        message (Message): The message object containing the necessary information.

    Returns:
        None: If the message text is not in the predefined command list.

    Raises:
        Exception: If an error occurs during the process.
    """
    try:
        # List of valid commands
        valid_commands = ["/start", "/help", "/change_city", "/current_weather",
                          "/weather_forecast", "/forecast_for_several_days",
                          "/weather_statistic", "/prediction"]
        # Check if the message is a valid command
        if message.text in valid_commands:
            # Insert the statistic data into the database
            fields = {"ts": message.date, "user_name": message.from_user.first_name,
                      "chat_id": message.chat.id, "action": message.text}
            builder = SQLQueryBuilder("statistic")
            builder.insert(fields)
            await execute_query(pool, builder.sql, *builder.args, fetch=True)
            log.debug("Statistic added successfully")
    except Exception as e:
        count_instance_errors.labels(instance=instance_id).inc()
        log.error(f"An error occurred during statistic adding: {e}")
        log.error("Exception traceback:", traceback.format_exc())


async def execute_query(
        pool: asyncpg.Pool,
        query: str,
        *args,
        fetch: bool = False,
        fetchval: bool = False,
        fetchrow: bool = False,
        execute: bool = False,
        max_retries: int = 3
) -> Optional[Union[asyncpg.Record, List[asyncpg.Record], int, None]]:
    """
    Execute the specified query using the provided connection pool.

    Args:
        pool (asyncpg.Pool): The connection pool to execute the query.
        query (str): The SQL query to execute.
        *args: Optional arguments to be passed with the query.
        fetch (bool): If True, fetch all results.
        fetchval (bool): If True, fetch a single value.
        fetchrow (bool): If True, fetch a single row.
        execute (bool): If True, execute the query without fetching.
        max_retries (int): The maximum number of retries.

    Returns:
        The result of the query based on the specified fetch method.

    Raises:
        Exception: If max retries exceeded.
    """
    retries = 0
    while retries < max_retries:
        try:
            async with pool.acquire() as connection:
                async with connection.transaction():
                    if fetch:
                        result = await connection.fetch(query, *args)
                        log.debug("fetch command executed successfully")
                    elif fetchval:
                        result = await connection.fetchval(query, *args)
                        log.debug("fetchval command executed successfully")
                    elif fetchrow:
                        result = await connection.fetchrow(query, *args)
                        log.debug("fetchrow command executed successfully")
                    elif execute:
                        result = await connection.execute(query, *args)
                        log.debug("execute command executed successfully")
                    else:
                        result = None
            return result
        except asyncpg.PostgresError as e:
            log.error(f"Database error: {e} {traceback.format_exc()}")
            database_errors_counters[0].labels(instance=instance_id).inc()  # database_connection_errors
            retries += 1
        except asyncpg.QueryCanceledError as e:
            log.error(f"Query canceled error: {e} {traceback.format_exc()}")
            database_errors_counters[1].labels(instance=instance_id).inc()  # database_query_errors
            retries += 1
        except RuntimeError as e:
            log.error(f"Runtime error: {e} {traceback.format_exc()}")
            database_errors_counters[3].labels(instance=instance_id).inc()
            retries += 1
        except Exception as e:
            log.error(f"Unexpected error: {e} {traceback.format_exc()} {query} {args}")
            database_errors_counters[2].labels(instance=instance_id).inc()  # database_other_errors

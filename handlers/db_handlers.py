import traceback
from fastapi import APIRouter, Depends, Security
from handlers.db_query_builder import execute_users_actions, execute_actions_count
import logging
from asyncpg import Pool
from postgres.pool import DbPool
from fastapi import HTTPException
from config.config import get_settings, Settings
from fastapi.security import HTTPBasicCredentials, HTTPBasic

security = HTTPBasic()

log = logging.getLogger(__name__)
bd_router = APIRouter()


def verify_credentials(credentials: HTTPBasicCredentials = Depends(security),
                       settings: Settings = Depends(get_settings)):
    """
    Function to verify the provided credentials.
    Args:
        credentials (HTTPBasicCredentials): The credentials to be verified.
        settings (Settings): The application settings.
    Returns:
        HTTPBasicCredentials: The verified credentials if successful.
    Raises:
        HTTPException: If the credentials are incorrect.
    """
    try:
        correct_username = settings.GET_USER
        correct_password = settings.GET_PASSWORD
        # Check if the provided credentials match the correct username and password
        if credentials.username == correct_username and credentials.password == correct_password:
            log.info("Credentials verified successfully")
            return credentials
    except HTTPException as e:
        log.debug("An error occurred: %s", str(e))
        log.debug("Exception traceback", traceback.format_exc())
        raise HTTPException(status_code=401, detail="Incorrect username or password")


@bd_router.get("/users_actions")
async def ex_users_actions(chat_id: int = None,
                           from_ts: int = None,
                           until_ts: int = None,
                           limits: int = 1000,
                           credentials: HTTPBasicCredentials = Security(verify_credentials),
                           pool: Pool = Depends(DbPool.get_pool)):
    """
      Retrieves user actions based on the provided criteria.
      Args:
          chat_id (int): The ID of the chat/user.
          from_ts (int, optional): The starting timestamp. Defaults to None.
          until_ts (int, optional): The ending timestamp. Defaults to None.
          limit (int, optional): The maximum number of results to retrieve. Defaults to 1000.
          credentials (HTTPBasicCredentials, optional): Security credentials. Defaults to Security(verify_credentials).
          pool (Pool, optional): The global database connection pool. Defaults to Depends(create_pool).
      Returns:
          list: The list of user actions retrieved based on the criteria.
      Raises:
          HTTPException: If there is an unauthorized access or an error occurs during retrieval.
      """

    try:
        res = await execute_users_actions(pool, chat_id, from_ts, until_ts, limits)
        return res
    except Exception as e:
        log.error("An error occurred: %s", str(e))
        log.debug(f"Exception traceback:\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


@bd_router.get("/actions_count")
async def get_actions_count(chat_id: int,
                            credentials: HTTPBasicCredentials = Security(verify_credentials),
                            pool: Pool = Depends(DbPool.get_pool)):
    """
     Retrieves the count of actions based on the provided chat_id.

     Args:
         chat_id (int): The ID of the chat/user.
         credentials (HTTPBasicCredentials, optional): Security credentials. Defaults to Security(verify_credentials).
         pool (Pool, optional): The global database connection pool. Defaults to Depends(create_pool).

     Returns:
         dict: The count of actions based on the provided chat_id.

     Raises:
         HTTPException: If there is an unauthorized access or an error occurs during retrieval.
     """
    try:
        res = await execute_actions_count(pool, chat_id)
        return res
    except Exception as e:
        log.error("An error occurred: %s", str(e))
        log.debug(f"Exception traceback:\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

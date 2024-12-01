import logging
import traceback
from telebot.async_telebot import AsyncTeleBot
from asyncpg.pool import Pool
from config.config import get_settings, Settings, get_bot
import json
from helpers.model_message import Message
from helpers.check_values import check_chat_id, check_waiting, handlers
from pydantic import ValidationError
from typing import Annotated
from fastapi import Request, HTTPException, Depends, APIRouter
from postgres.pool import DbPool
from prometheus.couters import instance_id, count_instance_errors, validation_error

log = logging.getLogger(__name__)

webhook_router = APIRouter()


@webhook_router.post("/tg_webhooks")
async def tg_webhooks(request: Request, config: Annotated[Settings, Depends(get_settings)],
                      bot: AsyncTeleBot = Depends(get_bot), pool: Pool = Depends(DbPool.get_pool)):
    """
    Handle incoming Telegram webhook requests.

    Parameters:
    - request: Request object containing the incoming request data
    - config: Settings configuration
    - bot: AsyncTeleBot instance for interacting with Telegram API
    - pool: Pool object for database connection

    Returns:
    - HTTPException: If there are errors in processing the request.

    This function handles incoming Telegram webhook requests and processes the received message.
    It first validates the `X-Telegram-Bot-Api-Secret-Token` header to ensure that the request is authorized.
    If the token is valid, it checks if the request method is `POST`. If it is, it parses the request body as JSON.
    It then creates a `Message` object from the JSON data and checks the chat ID.
    If the user is waiting for a value to be entered, it calls the `check_waiting` function.
    Otherwise, it calls the `handlers` function to process the message.
    If any exceptions occur during processing, it logs the error and sends a Telegram message with an error message.
    If the request method is not `POST`, it returns an HTTPException with a 405 status code.
    If the `X-Telegram-Bot-Api-Secret-Token` is invalid, it returns an HTTPException with a 401 status code.
    If there is a JSON decoding error or validation error, it returns an HTTPException with a 400 status code.
    """
    # Get X-Telegram-Bot-Api-Secret-Token from headers
    x_telegram_bot_api_secret_token = request.headers.get('X-Telegram-Bot-Api-Secret-Token')
    # Check if the X-Telegram-Bot-Api-Secret-Token is correct
    if x_telegram_bot_api_secret_token == config.SECRET_TOKEN_TG_WEBHOOK:
        if request.method == 'POST':
            try:
                json_dict = await request.json()

            except json.JSONDecodeError:
                log.error("Telegram webhook request body: JSONDecodeError")
                log.debug("Exception traceback", traceback.format_exc())
                raise HTTPException(status_code=400,
                                    detail="JSONDecodeError: An error occurred, please try again later")
            try:
                # Adjust JSON data and create a Message object
                json_dict['message']['from_user'] = json_dict['message'].pop('from')
                message = Message(**json_dict['message'])
            except ValidationError:
                log.error("ValidationError occurred Message")
                log.debug(traceback.format_exc())
                validation_error.labels(instance=instance_id).inc(0)
                raise HTTPException(status_code=400,
                                    detail="ValidationError: An error occurred, please try again later")
            try:
                # Check the chat ID and process the message accordingly
                status_user = await check_chat_id(pool, message)
                # Check if user is waiting for a value to be entered
                if "waiting_value" in status_user.values():
                    await check_waiting(status_user, pool, message, bot,
                                        config)  # Check if user is waiting for a value to be entered
                else:
                    await handlers(pool, message, bot, config,
                                   status_user)  # Process the message if user is not waiting for a value to be entered
            except Exception as exc:
                log.error("An error occurred: %s", str(exc))
                log.debug("Exception traceback", traceback.format_exc())
                count_instance_errors.labels(instance=instance_id).inc()
                return bot.send_message(message.chat.id, "An error occurred, please try again later")
        else:
            log.error(f"Invalid request method: {request.method}")
            log.debug("Exception traceback", traceback.format_exc())
            return HTTPException(status_code=405, detail="Method not allowed")
    else:
        log.error(f"Invalid X-Telegram-Bot-Api-Secret-Token: {x_telegram_bot_api_secret_token}")
        return HTTPException(status_code=401, detail="Unauthorized")

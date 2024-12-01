from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
from telebot.async_telebot import AsyncTeleBot
import logging

log = logging.getLogger(__name__)


class Settings(BaseSettings):
    TOKEN: str
    API_KEY: str
    TG_BOT_API_URL: str
    APP_DOMAIN: str
    LOG_LEVEL: str = 'DEBUG'
    SECRET_TOKEN_TG_WEBHOOK: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    GET_USER: str
    GET_PASSWORD: str
    GF_SECURITY_ADMIN_USER: str = "ADMIN_GF"
    GF_SECURITY_ADMIN_PASSWORD: str = "ADMIN_GF"
    POOL_HOST_DB: str = "localhost"
    NGROK_AUTHTOKEN: str
    LISTEN_PORT: int
    LOG_LEVEL_UVICORN: str

    model_config = SettingsConfigDict(env_file="../.env")


@lru_cache
def get_settings() -> Settings:
    return Settings()


@lru_cache
def get_bot() -> AsyncTeleBot:
    token = get_settings().TOKEN
    bot = AsyncTeleBot(token)
    return bot

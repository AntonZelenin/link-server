import os
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

from mess_message import constants


class Settings(BaseSettings):
    db_url: str
    async_db_url: str
    redis_url: str
    redis_port: int = 6379
    debug: bool = False

    num_of_chats_to_per_page: int = 30

    def __init__(self):
        if os.environ.get('ENVIRONMENT', 'dev') == 'dev':
            Settings.model_config = SettingsConfigDict(env_file=constants.DEV_ENV_FILE)

        super().__init__()


@lru_cache
def get_settings() -> Settings:
    return Settings()

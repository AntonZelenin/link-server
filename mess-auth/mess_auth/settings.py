import os
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

from mess_auth import constants


class Settings(BaseSettings):
    db_url: str
    async_db_url: str
    # to get a string like this run:
    # openssl rand -hex 32
    jwt_secret_key: str
    jwt_kid: str
    access_token_expire_minutes: int
    refresh_token_expire_minutes: int

    def __init__(self):
        if os.environ.get('ENVIRONMENT', 'dev') == 'dev':
            Settings.model_config = SettingsConfigDict(env_file=constants.DEV_ENV_FILE)

        super().__init__()


@lru_cache
def get_settings():
    return Settings()

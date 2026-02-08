import os
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

from mess_user import constants


class Settings(BaseSettings):
    db_url: str
    async_db_url: str
    auth_url: str

    def __init__(self):
        if os.environ.get('ENVIRONMENT', 'dev') == 'dev':
            Settings.model_config = SettingsConfigDict(env_file=constants.DEV_ENV_FILE)

        super().__init__()


@lru_cache
def get_settings():
    return Settings()

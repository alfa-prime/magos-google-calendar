from functools import lru_cache
from pathlib import Path
from pydantic import computed_field
from pydantic_core import MultiHostUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    API_KEY: str
    LOGS_LEVEL: str
    DB_ECHO: bool = True

    CALENDAR_ID: str
    CREDENTIALS_FILE: Path = Path("creds/credentials.json")
    TOKEN_FILE: Path = Path("creds/token.json")
    SCOPES: list[str] = ["https://www.googleapis.com/auth/calendar.readonly"]

    POSTGRES_SERVER: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_PORT: int = 5432

    @computed_field
    @property
    def DATABASE_URL(self) -> str:  # noqa
        return str(
            MultiHostUrl.build(
                scheme="postgresql+asyncpg",
                username=self.POSTGRES_USER,
                password=self.POSTGRES_PASSWORD,
                host=self.POSTGRES_SERVER,
                port=self.POSTGRES_PORT,
                path=self.POSTGRES_DB,
            )
        )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings():
    return Settings()  # noqa


settings = get_settings()

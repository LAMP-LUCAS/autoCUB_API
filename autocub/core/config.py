import os
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"

    # PostgreSQL Database
    POSTGRES_USER: str = "autocub_user"
    POSTGRES_PASSWORD: str = "autocub_pass"
    POSTGRES_DB: str = "cub"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    DATABASE_URL: Optional[str] = None

    # Redis (Celery Broker & Cache)
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_URL: Optional[str] = None

    # API Configuration
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8002
    API_PREFIX: str = "/v1"
    API_TITLE: str = "AutoCUB API"
    API_VERSION: str = "v1.1.0"
    API_DESCRIPTION: str = (
        "API RESTful para consulta e integração de dados estruturados do "
        "Custo Unitário Básico da Construção Civil (CUB/m² — NBR 12.721:2006). "
        "Solução irmã do AutoSINAPI e integrante do ecossistema Mundo AEC."
    )

    # Coleta Ética e Caching
    CUB_BASE_URL: str = "http://www.cub.org.br"
    CUB_REQUEST_DELAY_SECONDS: float = 3.0
    CUB_DOWNLOAD_DIR: str = "autocub_downloads"
    CUB_MAX_RETRIES: int = 3

    @property
    def get_database_url(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    @property
    def get_redis_url(self) -> str:
        if self.REDIS_URL:
            return self.REDIS_URL
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"


settings = Settings()

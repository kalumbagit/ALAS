from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import Optional, List

class Settings(BaseSettings):
    # --- Database ---
    DB_HOST: str
    DB_PORT: int
    DB_NAME: str
    DB_USER: str
    DB_PASSWORD: str
    DB_ENGINE: str = "postgres"

    # --- App ---
    APP_NAME: str
    APP_VERSION: str
    APP_TYPE: str
    API_VERSION: str
    APP_ENV: str
    APP_PORT: int
    DEBUG: bool

    # --- Redis ---
    REDIS_HOST: str
    REDIS_PORT: int
    REDIS_DB_DEFAULT: int
    REDIS_DB_TOKEN_CACHE: int
    REDIS_DB_REQUEST_CACHE: int

    # --- Security ---
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    REFRESH_TOKEN_EXPIRE_DAYS: int

    # --- Logging ---
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"

    # --- CORS ---
    CORS_ORIGINS: List[str] = ["http://10.22.185.238:5173", "http://127.0.0.1:3000","http://192.168.189.1:5173","http://192.168.65.1:5173"]

    # --- Allowed Hosts ---
    ALLOWED_HOSTS: List[str] = ["*"]

    # --- DB URL ---
    DB_URL: str | None = None

    # --- Minio ---
    MINIO_ENDPOINT: str
    MINIO_ACCESS_KEY: str
    MINIO_SECRET_KEY: str
    MINIO_SECURE: bool
    MINIO_DEFAULT_BUCKET:str
    MINIO_BUCKET_DELIVERER_IDENTITY: str
    MINIO_BUCKET_MERCHANT_DOCS: str
    MINIO_BUCKET_USER_AVATARS: str

    # ✅ Nouvelle syntaxe Pydantic v2
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore"
    }

    @field_validator("DB_URL", mode="before")
    def build_db_url(cls, v, info):
        if v:
            return v
        values = info.data
        engine = values.get("DB_ENGINE", "postgres")
        user = values.get("DB_USER")
        password = values.get("DB_PASSWORD")
        host = values.get("DB_HOST")
        port = values.get("DB_PORT", 5432)
        db_name = values.get("DB_NAME")

        if engine == "postgres":
            return f"postgresql://{user}:{password}@{host}:{port}/{db_name}"
        elif engine == "sqlite":
            return f"sqlite:///{db_name or 'app'}.db"
        raise ValueError(f"Unsupported DB_ENGINE: {engine}")

    @field_validator("JWT_SECRET")
    def check_jwt_secret(cls, v):
        if not v or v.strip() == "":
            raise ValueError("JWT_SECRET must be defined in environment or .env")
        return v


settings = Settings()

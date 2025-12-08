from pydantic_settings import BaseSettings, SettingsConfigDict
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
    DEBUG: bool = False

    # --- Redis ---
    REDIS_HOST: str
    REDIS_PORT: int
    REDIS_DB: int

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

    # --- DB URL générée dynamiquement ---
    DB_URL: Optional[str] = None

    # --- Minio ---
    MINIO_ENDPOINT: str
    MINIO_ACCESS_KEY: str
    MINIO_SECRET_KEY: str
    MINIO_SECURE: bool
    MINIO_BUCKET_DELIVERER_IDENTITY: str
    MINIO_BUCKET_MERCHANT_DOCS: str
    MINIO_BUCKET_USER_AVATARS: str

    # ==========================
    # 🔹 Validators (v2 syntax)
    # ==========================

    @field_validator("DB_URL", mode="before")
    def build_db_url(cls, v, info):
        """
        Construit dynamiquement l'URL de la base à partir des autres variables.
        """
        if v:
            return v

        data = info.data or {}
        engine = data.get("DB_ENGINE", "postgres")

        if engine == "postgres":
            return (
                f"postgresql://{data.get('DB_USER')}:{data.get('DB_PASSWORD')}"
                f"@{data.get('DB_HOST')}:{data.get('DB_PORT')}/{data.get('DB_NAME')}"
            )
        elif engine == "sqlite":
            return f"sqlite:///{data.get('DB_NAME', 'app')}.db"
        else:
            raise ValueError("Unsupported DB_ENGINE type")

    @field_validator("JWT_SECRET")
    def check_jwt_secret(cls, v):
        if not v or v.strip() == "":
            raise ValueError("JWT_SECRET must be defined in environment or .env")
        return v

    @field_validator("CORS_ORIGINS", mode="before")
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v


    # ==========================
    # 🔹 Config du modèle
    # ==========================
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()

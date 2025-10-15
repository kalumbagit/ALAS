from pydantic import BaseSettings, validator

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
    APP_VERSION: str = "1.0.0"
    APP_ENV: str 
    APP_PORT: int
    DEBUG: bool

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
    LOG_FORMAT: str = "json"  # "json" ou "console"

    # --- CORS ---
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]

    # --- Allowed Hosts ---
    ALLOWED_HOSTS: list[str] = ["*"]

    # --- DB URL générée dynamiquement ---
    DB_URL: str | None = None

    @validator("DB_URL", pre=True, always=True)
    def build_db_url(cls, v, values):
        """
        Construit dynamiquement l'URL de la base à partir des autres variables.
        """
        if v:
            return v
        engine = values.get("DB_ENGINE", "postgres")
        if engine == "postgres":
            return f"postgres://{values.get('DB_USER')}:{values.get('DB_PASSWORD')}@{values.get('DB_HOST')}:{values.get('DB_PORT')}/{values.get('DB_NAME')}"
        elif engine == "sqlite":
            return f"sqlite:///{values.get('DB_NAME', 'app')}.db"
        else:
            raise ValueError("Unsupported DB_ENGINE type") 
    
    @validator("JWT_SECRET")
    def check_jwt_secret(cls, v):
        if not v or v.strip() == "":
            raise ValueError("JWT_SECRET must be defined in environment or .env")
        return v
    class Config:
        env_file = ".env"
        extra = "ignore"  # ignore les variables non utilisées

settings = Settings()

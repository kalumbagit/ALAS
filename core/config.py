from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # --- Database ---
    DB_HOST: str
    DB_PORT: int
    DB_NAME: str
    DB_USER: str
    DB_PASSWORD: str

    # --- App ---
    APP_NAME: str
    APP_ENV: str
    APP_PORT: int
    DEBUG: bool 


    # --- Redis ---
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
 

    # --- Security ---

    JWT_SECRET: str
    JWT_ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int

    class Config:
        env_file = ".env"
        extra = "ignore"  # pour éviter les erreurs si d'autres variables sont ajoutées

settings = Settings()

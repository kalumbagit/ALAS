from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    APP_NAME: str = "SteBor Tech API"
    DEBUG: bool = True
    DATABASE_URL: str = "postgres://postgres:password@localhost:5432/ste_bor_db"

    class Config:
        env_file = ".env"

settings = Settings()

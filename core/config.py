from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DEBUG: bool 
    APP_NAME: str
    APP_ENV: str
    DB_HOST: str
    DB_PORT: int
    DB_NAME: str
    DB_USER: str
    DB_PASSWORD: str
    JWT_SECRET: str
    JWT_ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int

    class Config:
        env_file = ".env"

settings = Settings()

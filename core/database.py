from tortoise.contrib.fastapi import register_tortoise
from fastapi import FastAPI
from core.config import settings

DB_URL = f"postgres://{settings.DB_USER}:{settings.DB_PASSWORD}@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"

def init_db(app: FastAPI):
    register_tortoise(
        app,
        db_url=DB_URL,
        modules={"models": ["app.models.user_model"]},
        generate_schemas=True,
        add_exception_handlers=True,
    )

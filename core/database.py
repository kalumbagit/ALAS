from tortoise.contrib.fastapi import register_tortoise
from fastapi import FastAPI
from core.config import settings

def init_db(app: FastAPI):
    register_tortoise(
        app,
        db_url=settings.DATABASE_URL,
        modules={"models": ["app.models.user_model", "app.models.product_model"]},
        generate_schemas=True,
        add_exception_handlers=True,
    )

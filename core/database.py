from fastapi import FastAPI
from tortoise.contrib.fastapi import register_tortoise
from core.config import settings

# --- Database URL ---
DB_URL = f"postgres://{settings.DB_USER}:{settings.DB_PASSWORD}@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"

# --- Configuration globale Tortoise ORM (utilisée par Aerich) ---
TORTOISE_ORM = {
    "connections": {
        "default": DB_URL,
    },
    "apps": {
        "models": {
            "models": [
                "models.user_model",  # Chemin complet vers ton modèle utilisateur
                "aerich.models",          # Toujours inclure Aerich ici
            ],
            "default_connection": "default",
        },
    },
}

# --- Initialisation de la base pour FastAPI ---
def init_db(app: FastAPI):
    register_tortoise(
        app,
        config=TORTOISE_ORM,           # ✅ On passe la config complète ici
        generate_schemas=False,        # ❌ PAS d’auto-génération => on laisse Aerich gérer
        add_exception_handlers=True,
    )

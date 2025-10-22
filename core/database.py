from fastapi import FastAPI
from tortoise.contrib.fastapi import register_tortoise
from core.config import settings
from core.logging import logger
from tortoise import Tortoise
from tortoise.exceptions import OperationalError
from tortoise.transactions import in_transaction
from typing import AsyncGenerator


TORTOISE_ORM={
            "connections": {
                "default": {
                    "engine": "tortoise.backends.asyncpg" if settings.DB_URL.startswith("postgres") else "tortoise.backends.sqlite",
                    "credentials": {
                        "host": settings.DB_HOST,
                        "port": settings.DB_PORT,
                        "user": settings.DB_USER,
                        "password": settings.DB_PASSWORD,
                        "database": settings.DB_NAME
                    } if settings.DB_URL.startswith("postgres") else {
                        "file_path": settings.DB_URL.replace("sqlite:///", ""),
                    }
                }
            },
            "apps": {
                "models": {
                    "models": [
                        "models.category_model",
                        "models.product_model",
                        "aerich.models"  # Pour les migrations
                    ],
                    "default_connection": "default",
                }
            },
            "use_tz": False,
            "timezone": "UTC",
        }

async def init_db(app: FastAPI = None) -> None:
    """
    Initialise la connexion à la base de données
    """
    try:
        logger.info("📊 Initialisation de la base de données...")

        # ✅ Initialise Tortoise ORM une seule fois
        await Tortoise.init(config=TORTOISE_ORM)
        logger.info("📦 Tortoise ORM initialisé (connexion établie).")
        
        if app:
            # Intégration avec FastAPI
            register_tortoise(
                app,
                config=TORTOISE_ORM,           # ✅ On passe la config complète ici
                generate_schemas=False,     # ❌ PAS d’auto-génération => on laisse Aerich gérer
                add_exception_handlers=True,
            )
            logger.info("✅ Base de données initialisée avec FastAPI")
        else:
            # Initialisation standalone
            await Tortoise.init(config=db_config)
            await Tortoise.generate_schemas()
            logger.info("✅ Base de données initialisée en mode standalone")
            
    except Exception as e:
        logger.error(f"❌ Erreur lors de l'initialisation de la base de données: {str(e)}")
        raise

async def close_db():
    """
    Ferme proprement toutes les connexions à la base de données Tortoise ORM.
    À appeler dans le bloc finally du lifespan.
    """
    try:
        if Tortoise._inited:
            logger.info("🔌 Fermeture des connexions à la base de données...")
            await Tortoise.close_connections()
            logger.info("✅ Connexions fermées correctement.")
        else:
            logger.info("ℹ️ Aucune connexion ouverte à fermer.")
    except Exception as e:
        logger.error(f"❌ Erreur lors de la fermeture des connexions DB: {str(e)}", exc_info=True)
    
async def get_db() -> AsyncGenerator:
    """
    Fournit une connexion DB utilisable avec Depends() dans FastAPI.
    """
    try:
        async with in_transaction() as conn:
            yield conn
    except OperationalError as e:
        logger.error(f"⚠️ Problème de connexion à la base de données : {e}")
        raise
    except Exception as e:
        logger.error(f"❌ Erreur inattendue d'accès DB : {e}", exc_info=True)
        raise
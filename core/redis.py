import time
import aioredis
import redis as redis_sync
from typing import Any, Optional
from core.config import settings
from core.logging import logger


class RedisService:
    """
    Service centralisé de gestion Redis pour le cache, les tokens et autres données.
    Gère à la fois les connexions asynchrones et synchrones.
    """

    def __init__(
        self,
        db_index: int = settings.REDIS_DB_REQUEST_CACHE,
    ):
        """
        Initialise les connexions Redis (async et sync)
        """
        self.host = settings.REDIS_HOST
        self.port = settings.REDIS_PORT
        self.db_default = db_index

        # Connexions
        self._async_client = aioredis.from_url(
                f"redis://{self.host}:{self.port}/{self.db_default}",
                decode_responses=True
            )
        
        self._sync_client = redis_sync.Redis(
                host=self.host,
                port=self.port,
                db=self.db_default,
                decode_responses=True
            )

    

    # -------------------------------------------------
    # 🧠 MÉTHODES DE GESTION GÉNÉRIQUE
    # -------------------------------------------------
    async def set_data(self, key: str, value: Any, ttl: Optional[int] = None):
        """
        Enregistre une donnée dans Redis avec TTL optionnel (asynchrone)
        """
        try:
            await self._async_client.set(key, value, ex=ttl)
        except Exception as e:
            logger.warning(f"Erreur Redis SET {key}: {e}")
            return None

    async def get_data(self, key: str) -> Optional[str]:
        """
        Récupère une donnée dans Redis (asynchrone)
        """
        try:
            return await self._async_client.get(key)
        except Exception as e:
            logger.warning(f"Erreur Redis GET {key}: {e}")
            return None

    async def delete_data(self, key: str):
        """
        Supprime une clé dans Redis (asynchrone)
        """
        try:
            await self._async_client.delete(key)
        except Exception as e:
            logger.warning(f"Erreur Redis DELETE {key}: {e}")
            return None

    # -------------------------------------------------
    # ⚡ MÉTHODES UTILITAIRES (SYNCHRONES)
    # -------------------------------------------------
    def sync_set_data(self, key: str, value: Any, ttl: Optional[int] = None):
        """
        Version synchrone de set_data()
        """
        try:
            self._sync_client.set(key, value, ex=ttl)
        except Exception as e:
            logger.warning(f"Erreur Redis SET {key}: {e}")
            return None

    def sync_get_data(self, key: str) -> Optional[str]:
        """
        Version synchrone de get_data()
        """
        try:
            return self._sync_client.get(key)
        except Exception as e:
            logger.warning(f"Erreur Redis GET {key}: {e}")
            return None

    def sync_delete_data(self, key: str):
        """
        Version synchrone de delete_data()
        """
        try:
            self._sync_client.delete(key)
        except Exception as e:
            logger.warning(f"Erreur Redis DELETE {key}: {e}")
            return None
        

    # -------------------------------------------------
    # 🧹 MÉTHODES DE MAINTENANCE
    # -------------------------------------------------
    async def flush_db(self):
        """
        Vide complètement une base Redis (asynchrone)
        """
        try:
            await self._async_client.flushdb()
        except Exception as e:
            logger.warning(f"Erreur Redis DROP : {e}")
            return None
        

    def sync_flush_db(self):
        """
        Vide complètement une base Redis (synchrone)
        """
        try:
            self._sync_client.flushdb()
        except Exception as e:
            logger.warning(f"Erreur Redis DROP : {e}")
            return None

    async def close(self):
        """
        Ferme proprement la connexion asynchrone Redis.
        """
        if self._async_client:
            await self._async_client.close()


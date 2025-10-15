# core/redis.py
import aioredis
import time
from core.config import settings
import redis as RD


redis = aioredis.from_url(f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB}", decode_responses=True)

async def revoke_token(jti: str, exp_timestamp: int):
    """
    Stocke le token révoqué avec TTL
    """
    ttl = max(exp_timestamp - int(time.time()), 0)
    await redis.set(jti, "revoked", ex=ttl)

async def is_token_revoked(jti: str) -> bool:
    """
    Vérifie si le token est révoqué
    """
    return await redis.exists(jti) > 0


# Client Redis SYNCHRONE
redis_client_sync = RD.Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    db=settings.REDIS_DB,
    decode_responses=True,  # pour récupérer des str plutôt que bytes
)

from fastapi_jwt import JwtAccessBearer
import time
from core.redis import redis_client_sync,redis
from core.config import settings
from datetime import timedelta
from typing import Optional
from authlib.jose import jwt as jwtoken, JoseError
from core.exceptions import UnauthorizedException


# =========================
# ⚙️ Configuration globale
# =========================
jwt = JwtAccessBearer(
    secret_key=settings.JWT_SECRET,
    auto_error=True,
    access_expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    refresh_expires_delta=timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    algorithm=settings.JWT_ALGORITHM,
)


# =========================
# 🔍 Vérification denylist
# =========================
def check_if_token_in_denylist(payload: dict) -> bool:
    """
    Vérifie dans Redis si le token (via son JTI) est révoqué.
    """
    jti = payload.get("jti")
    if not jti:
        return True  # Si pas de JTI => token invalide

    try:
        is_revoked = redis_client_sync.exists(jti)
        return bool(is_revoked)
    except Exception as e:
        from core.logging import logger
        logger.warning(f"⚠️ Redis indisponible : impossible de vérifier JTI={jti} ({e})")
        return True


# =========================
# 🔐 Fonctions utilitaires
# =========================
def create_access_token(subject: str, extra_claims: Optional[dict] = None):
    """
    Génère un access token JWT.
    """
    claims = {"sub": subject}
    if extra_claims:
        claims.update(extra_claims)

    token = jwt.create_access_token(claims)
    return token


def create_refresh_token(subject: str):
    """
    Génère un refresh token JWT.
    """
    return jwt.create_refresh_token({"sub": subject})


async def revoke_token(jti: str, exp_timestamp: int):
    """
    Ajoute un token à la denylist (blacklist) dans Redis jusqu’à expiration.
    """
    ttl = max(exp_timestamp - int(time.time()), 0)
    if ttl == 0:
        return  # token déjà expiré

    try:
        await redis.set(jti, "revoked", ex=ttl)
    except Exception as e:
        from core.logging import logger
        logger.warning(f"⚠️ Impossible d’ajouter le token JTI={jti} à la denylist : {e}")


# =========================
# 🔓 Décodage des tokens
# =========================
def decode_token(token: str):
    try:
        if isinstance(token, bytes):
            token = token.decode("utf-8")
        # Enlève TOUS les "Bearer " possibles
        token = token.replace("Bearer ", "").replace("bearer ", "").strip()

        # Si le token contient un point en trop (concat), nettoie
        parts = token.split(".")
        if len(parts) > 3:
            token = ".".join(parts[:3])

        secret = settings.JWT_SECRET
        if isinstance(secret, bytes):
            secret = secret.decode("utf-8")

        claims = jwtoken.decode(token, key=secret)
        claims.validate()
        return claims
    except Exception as e:
        raise UnauthorizedException(detail=f"Token invalide ou expiré : {e}")


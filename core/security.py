from fastapi_jwt_auth import AuthJWT
from core.redis import redis_client_sync  # client Redis synchrone
from core.config import settings

from pydantic import BaseModel, ConfigDict


class JWTSettings(BaseModel):
    authjwt_secret_key: str = settings.JWT_SECRET
    authjwt_algorithm: str = settings.JWT_ALGORITHM
    authjwt_denylist_enabled: bool = True
    authjwt_denylist_token_checks = {"access", "refresh"}

    model_config = ConfigDict(from_attributes=True)

@AuthJWT.load_config
def get_config():
    return JWTSettings()



def check_if_token_in_denylist(decrypted_token):
    """
    Vérifie de manière SYNCHRONE si le token a été révoqué.
    Doit être rapide et non-bloquante.
    """
    jti = decrypted_token.get("jti")
    if not jti:
        return True  # token invalide => considéré comme révoqué

    # Redis synchrone
    try:
        is_revoked = redis_client_sync.exists(jti)  # 1 si existe, 0 sinon
        return is_revoked == 1
    except Exception:
        # Si Redis est down, on considère le token comme révoqué pour sécurité
        return True

# On charge la config
@AuthJWT.token_in_denylist_loader
def token_in_denylist_callback(decrypted_token):
    return check_if_token_in_denylist(decrypted_token)



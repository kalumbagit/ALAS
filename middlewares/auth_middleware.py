# app/middleware/auth_middleware.py
from typing import Optional, Dict, Any
from fastapi import Request, HTTPException, status,Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError, ExpiredSignatureError
from core.logging import logger
from core.config import settings
from core.exceptions import UnauthorizedException,InternalServerException
from core.redis import RedisService
import time

# Cache pour les tokens vérifiés (optionnel, pour la performance)
client=RedisService(db_index=settings.REDIS_DB_TOKEN_CACHE)
class AuthMiddleware(HTTPBearer):
    """
    Middleware d'authentification professionnel avec gestion avancée des tokens
    """
    
    def __init__(self, auto_error: bool = True):
        super().__init__(auto_error=auto_error)
        self.jwt_secret = settings.JWT_SECRET
        self.jwt_algorithm = settings.JWT_ALGORITHM
        self.allowed_user_types = {"merchant", "admin", "super_admin"}  # Configurable

    async def __call__(self, request: Request) -> Optional[Dict[str, Any]]:
        """
        Vérifie et valide le token JWT pour les marchands et administrateurs
        """
        try:
            credentials: HTTPAuthorizationCredentials = await super().__call__(request)
            if not credentials:
                raise UnauthorizedException(detail="Token d'authentification manquant")

            return await self.verify_token(request, credentials.credentials)
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Erreur inattendue lors de l'authentification: {e}")
            raise InternalServerException(detail="Erreur d'authentification")

    async def verify_token(self, request: Request, token: str) -> Dict[str, Any]:
        """
        Vérifie et décode le token JWT
        """
        # 1️⃣ Vérification du cache (si déjà validé récemment)
        cached_payload = await client.get_data(token)
        if cached_payload:
            self._inject_user_data(request, cached_payload)
            return cached_payload

        try:
            # Décodage et validation du token
            payload = jwt.decode(
                token, 
                self.jwt_secret, 
                algorithms=[self.jwt_algorithm],
                options={
                    "verify_signature": True,
                    "require_exp": True,
                    "verify_exp": True
                }
            )

            # 3️⃣ Validation des claims
            self._validate_payload(payload)

            # 4️⃣ Vérification des permissions
            self._check_permissions(payload)

            # 5️⃣ Injection des données utilisateur
            self._inject_user_data(request, payload)

            # 6️⃣ Mise en cache avec TTL (basé sur l'expiration du token)
            exp_timestamp = payload.get("exp")
            current_time = int(time.time())
            ttl = max(exp_timestamp - current_time, 0)  # éviter les valeurs négatives

            # Stockage du payload sous forme de string JSON
            await client.set_data(key=token, value=payload, ttl=ttl)
            
            logger.info(f"Authentification réussie pour l'utilisateur {payload.get('user_id')}")
            return payload

        except ExpiredSignatureError:
            logger.warning("Tentative d'accès avec token expiré")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token expiré"
            )
        except JWTError as e:
            logger.warning(f"Token JWT invalide: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token invalide"
            )
        except PermissionError as e:
            logger.warning(f"Permission refusée: {e}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=str(e)
            )

    def _validate_payload(self, payload: Dict[str, Any]) -> None:
        """
        Valide la présence des claims requis dans le payload
        """
        required_claims = {"user_id", "user_type", "exp"}
        missing_claims = required_claims - set(payload.keys())
        
        if missing_claims:
            raise JWTError(f"Claims manquants dans le token: {missing_claims}")

        # Validation du format de l'user_id
        user_id = payload.get("user_id")
        if not user_id or not isinstance(user_id, (str, int)):
            raise JWTError("user_id invalide dans le token")

        # Validation du type d'utilisateur
        user_type = payload.get("user_type")
        if not user_type or not isinstance(user_type, str):
            raise JWTError("user_type invalide dans le token")

    def _check_permissions(self, payload: Dict[str, Any]) -> None:
        """
        Vérifie les permissions de l'utilisateur
        """
        user_type = payload.get("user_type")
        
        if user_type not in self.allowed_user_types:
            raise PermissionError(
                f"Accès réservé aux {', '.join(self.allowed_user_types)}. "
                f"Type d'utilisateur: {user_type}"
            )

        # Vérification supplémentaire pour les marchands avec abonnement expiré
        if user_type == "merchant":
            subscription_status = payload.get("subscription_status")
            if subscription_status == "expired":
                logger.warning(f"Marchand {payload.get('user_id')} avec abonnement expiré")
                # Option: autoriser quand même ou bloquer?
                # raise PermissionError("Abonnement expiré")

    def _inject_user_data(self, request: Request, payload: Dict[str, Any]) -> None:
        """
        Injecte les données utilisateur dans l'objet request
        """
        request.state.user_data = {
            "user_id": payload.get("user_id"),
            "user_type": payload.get("user_type"),
            "subscription_type": payload.get("subscription_type", "free"),
            "subscription_status": payload.get("subscription_status", "active"),
            "permissions": payload.get("permissions", []),
            #"merchant_id": payload.get("merchant_id"),  # Si l'utilisateur gère un marchand spécifique
            "email": payload.get("email")
        }

# Instances réutilisables
auth_middleware = AuthMiddleware()

# Dépendances FastAPI spécifiques
async def get_current_merchant_or_admin(
    request: Request, 
    auth: Dict[str, Any] = Depends(auth_middleware)
) -> Dict[str, Any]:
    """
    Dépendance FastAPI pour récupérer l'utilisateur authentifié (marchand ou admin)
    """
    return request.state.user_data

async def get_current_admin(
    request: Request,
    auth: Dict[str, Any] = Depends(auth_middleware)
) -> Dict[str, Any]:
    """
    Dépendance FastAPI pour les administrateurs seulement
    """
    user_data = request.state.user_data
    if user_data["user_type"] not in {"admin", "super_admin"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès réservé aux administrateurs"
        )
    return user_data

async def get_current_merchant(
    request: Request,
    auth: Dict[str, Any] = Depends(auth_middleware)
) -> Dict[str, Any]:
    """
    Dépendance FastAPI pour les marchands seulement
    """
    user_data = request.state.user_data
    if user_data["user_type"] != "merchant":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Accès réservé aux marchands"
        )
    return user_data

# Utilitaires pour les contrôleurs
def get_current_user_id(request: Request) -> str:
    """Récupère l'ID de l'utilisateur depuis la requête"""
    return getattr(request.state.user_data, "user_id", None)

def get_current_user_type(request: Request) -> str:
    """Récupère le type d'utilisateur depuis la requête"""
    return getattr(request.state.user_data, "user_type", None)

def get_current_merchant_id(request: Request) -> Optional[str]:
    """Récupère l'ID du marchand depuis la requête"""
    return getattr(request.state.user_data, "merchant_id", None)


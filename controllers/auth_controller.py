from fastapi import APIRouter, HTTPException, status,Security
from fastapi.security import HTTPAuthorizationCredentials

from services.auth_service import AuthService
from schemas.user_schema import (
    LoginDataSchema,
    LoginResponseSchema,
    TokenResponseSchema,
    UserOutSchema
)
from core.exceptions import (
    APIException,
    NotFoundException,
    ConflictException,
    InternalServerException
)
from core.dependencies import access_security, refresh_security

from core.logging import logger

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)

auth_service = AuthService()


def handle_exception(e: Exception):
    """Transforme les exceptions métier en HTTPException pour FastAPI."""
    if isinstance(e, NotFoundException):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e.detail)
        )
    elif isinstance(e, ConflictException):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e.detail)
        )
    elif isinstance(e, APIException):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e.detail)
        )
    elif isinstance(e, InternalServerException):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur interne du serveur"
        )
    else:
        logger.exception(f"Erreur inattendue non gérée : {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Une erreur inattendue s'est produite."
        )


# ------------------------------
# Login
# ------------------------------
@router.post("/login", response_model=LoginResponseSchema, status_code=status.HTTP_200_OK)
async def login(data: LoginDataSchema):
    """
    Authentifie un utilisateur et retourne les tokens JWT.
    """
    try:
        return await auth_service.login(data)
    except Exception as e:
        handle_exception(e)


# ------------------------------
# Logout
# ------------------------------
@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(access: HTTPAuthorizationCredentials = Security(access_security),refresh: str = Security(refresh_security)):
    """
    Les deux tokens sont passés via les headers :
    - Authorization: Bearer <access_token>
    - X-Refresh-Token: <refresh_token>
    """
    try:
        access_token = access.credentials

        return await auth_service.logout(access_token, refresh)
    except Exception as e:
        handle_exception(e)

# ------------------------------
# Refresh token
# ------------------------------
@router.post("/refresh",dependencies=[Security(refresh_security)], response_model=TokenResponseSchema, status_code=status.HTTP_200_OK)
async def refresh(refresh: str = Security(refresh_security)):
    """
    Rafraîchit le token d'accès à l'aide du refresh token.
    """
    try:
        return await auth_service.refresh(refresh)
    except Exception as e:
        handle_exception(e)


# ------------------------------
# Get current user
# ------------------------------
@router.get("/me", response_model=UserOutSchema, status_code=status.HTTP_200_OK)
async def get_current_user(credentials: HTTPAuthorizationCredentials = Security(access_security)):
    """
    Récupère les informations de l'utilisateur actuellement connecté.
    """
    try:
        return await auth_service.get_current_user(credentials)
    except Exception as e:
        handle_exception(e)

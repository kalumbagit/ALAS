from fastapi import APIRouter, Depends, HTTPException, status
from fastapi_jwt_auth import AuthJWT

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
async def login(data: LoginDataSchema,Authorize: AuthJWT = Depends()):
    """
    Authentifie un utilisateur et retourne les tokens JWT.
    """
    try:
        return await auth_service.login(data,Authorize)
    except Exception as e:
        handle_exception(e)


# ------------------------------
# Logout
# ------------------------------
@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(Authorize: AuthJWT = Depends()):
    """
    Révoque le token actuel.
    """
    try:
        return await auth_service.logout(Authorize)
    except Exception as e:
        handle_exception(e)


# ------------------------------
# Refresh token
# ------------------------------
@router.post("/refresh", response_model=TokenResponseSchema, status_code=status.HTTP_200_OK)
async def refresh(Authorize: AuthJWT = Depends()):
    """
    Rafraîchit le token d'accès à l'aide du refresh token.
    """
    try:
        return await auth_service.refresh(Authorize)
    except Exception as e:
        handle_exception(e)


# ------------------------------
# Get current user
# ------------------------------
@router.get("/me", response_model=UserOutSchema, status_code=status.HTTP_200_OK)
async def get_current_user(Authorize: AuthJWT = Depends()):
    """
    Récupère les informations de l'utilisateur actuellement connecté.
    """
    try:
        return await auth_service.get_current_user(Authorize)
    except Exception as e:
        handle_exception(e)

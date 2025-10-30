from fastapi.security import HTTPAuthorizationCredentials
from core.dependencies import access_security
from core.security import decode_token

# Standard library
from typing import List, Optional
from pydantic import ValidationError

# Third-party libraries
from fastapi import APIRouter, HTTPException, Query, status,Depends

from models.user_model import User,UserType


# Local application imports
from schemas.user_schema import UserCreateSchema,UserUpdateSchema,UserOutSchema,UserStatusUpdateSchema,UserRatingUpdateSchema,DeleteResponseSchema,UserExistsResponseSchema,UserCountResponseSchema

from services.user_service import UserService
from core.exceptions import APIException,NotFoundException,ConflictException,InternalServerException,UnauthorizedException

from core.logging import logger


router = APIRouter(prefix="/users", tags=["Users - Customer Management"])

admin_router = APIRouter(prefix="/admin/manage/users",tags=["Admin - Customer Management"])

user_service = UserService()


# --------------------------------------
# Helpers pour la gestion centralisée
# --------------------------------------

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
    elif isinstance(e, UnauthorizedException):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e.detail)
        )
    elif isinstance(e, InternalServerException):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur interne du serveur"
        )
    elif isinstance(e, ValidationError):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=e.errors()
        )
    else:
        logger.exception(f"Erreur inattendue non gérée : {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Une erreur inattendue s'est produite."
        )

# ============================================================
# 🧩 Vérifie qu’un token d’accès valide est présent
# ============================================================
async def require_access_token(credentials: HTTPAuthorizationCredentials = Depends(access_security)) -> User:
    """
    Extrait et vérifie le token d’accès.
    Retourne l'utilisateur correspondant si le token est valide.
    """
    try:
        # Décodage du JWT
        access_payload = decode_token(credentials.credentials)
        
        # Extraction de l'user_id
        user_id = access_payload.get("sub") or access_payload.get("subject", {}).get("sub")

        if not user_id:
            raise UnauthorizedException(detail="Token invalide (pas d'identifiant utilisateur)")

        user = await User.get_or_none(id=user_id)
        if not user or not getattr(user, "is_active", True):
            raise UnauthorizedException(detail="Utilisateur inactif ou introuvable")

        return user

    except Exception as e:
        logger.warning(f"Erreur de vérification du token : {e}")
        raise UnauthorizedException(detail="Token d'accès invalide ou expiré")


# ============================================================
# 🧩 Vérifie que l’utilisateur est administrateur
# ============================================================
async def require_admin(credentials: HTTPAuthorizationCredentials = Depends(access_security)) -> User:
    """
    Vérifie que le token d’accès est valide et que l’utilisateur est un admin.
    """
    try:
        # Décodage du JWT
        access_payload = decode_token(credentials.credentials)
        
        # Extraction de l'user_id
        user_id = access_payload.get("sub") or access_payload.get("subject", {}).get("sub")

        if not user_id:
            raise UnauthorizedException(detail="Token invalide (pas d'identifiant utilisateur)")

        user = await User.get_or_none(id=user_id)
        if not user or user.user_type != UserType.ADMIN:
            raise UnauthorizedException(detail="Accès refusé — réservée aux administrateurs")

        return user

    except Exception as e:
        logger.warning(f"Tentative d'accès admin non autorisée : {e}")
        raise UnauthorizedException(detail="Token invalide ou expiré")
    
# --------------------------------------
# Création d’un utilisateur
# --------------------------------------

@router.post("/", response_model=UserOutSchema, status_code=status.HTTP_201_CREATED)
async def create_user(user: UserCreateSchema):
    try:
        return await user_service.create_user(user)
    except Exception as e:
        handle_exception(e)


# --------------------------------------
# Récupérer un utilisateur par ID
# --------------------------------------

@router.get("/{user_id}", response_model=UserOutSchema,dependencies=[Depends(require_access_token)])
async def get_user(user_id: str):
    try:
        user_id = user_id.strip('"')  # retire les guillemets accidentels
        return await user_service.get_user(user_id)
    except Exception as e:
        handle_exception(e)


# --------------------------------------
# Mise à jour complète (PUT) / partielle (PATCH)
# --------------------------------------

@router.patch("/{user_id}", response_model=UserOutSchema,dependencies=[Depends(require_access_token)])
async def update_user(user_id: str, user_data: UserUpdateSchema):
    try:
        user_id = user_id.strip('"')  # retire les guillemets accidentels
        return await user_service.update_user(user_id, user_data)
    except Exception as e:
        handle_exception(e)

# --------------------------------------
# Methodes reservés à l'administrations
# --------------------------------------

@admin_router.delete(
    "/{user_id}/deactivate",
    response_model=UserOutSchema,
    status_code=status.HTTP_200_OK,
    summary="Désactiver un utilisateur",
    description="Désactive un utilisateur (soft delete)",
    dependencies=[Depends(require_admin)]
)
async def deactivate_user(user_id: str):
    try:
        user_id = user_id.strip('"')  # retire les guillemets accidentels
        return await user_service.deactivate_user(user_id)
    except Exception as e:
        handle_exception(e)

@admin_router.patch(
    "/{user_id}/activate",
    response_model=UserOutSchema,
    status_code=status.HTTP_200_OK,
    summary="Activer un utilisateur",
    description="Active un utilisateur précédemment désactivé",
    dependencies=[Depends(require_admin)]
)
async def activate_user(user_id: str):
    try:
        user_id = user_id.strip('"')  # retire les guillemets accidentels
        return await user_service.activate_user(user_id)
    except Exception as e:
        handle_exception(e)

@admin_router.patch(
    "/{user_id}/status",
    response_model=UserOutSchema,
    status_code=status.HTTP_200_OK,
    summary="Mettre à jour le statut",
    description="Met à jour le statut actif/inactif d'un utilisateur",
    dependencies=[Depends(require_admin)]
)
async def update_user_status(
    user_id: str,
    status_data: UserStatusUpdateSchema
):
    try:
        user_id = user_id.strip('"')  # retire les guillemets accidentels
        return await user_service.update_user_status(user_id, status_data)
    except Exception as e:
        handle_exception(e)

@admin_router.patch(
    "/{user_id}/verify",
    response_model=UserOutSchema,
    status_code=status.HTTP_200_OK,
    summary="Vérifier un utilisateur",
    description="Marque un utilisateur comme vérifié",
    dependencies=[Depends(require_admin)]
)
async def verify_user(user_id: str):
    try:
        user_id = user_id.strip('"')  # retire les guillemets accidentels
        return await user_service.verify_user(user_id)
    except Exception as e:
        handle_exception(e)

@admin_router.patch(
    "/{user_id}/rating",
    response_model=UserOutSchema,
    status_code=status.HTTP_200_OK,
    summary="Mettre à jour la note",
    description="Met à jour la note moyenne d'un utilisateur",
    dependencies=[Depends(require_admin)]
)
async def update_user_rating(
    user_id: str,
    rating_data: UserRatingUpdateSchema  # Schema avec champ 'rating'
):
    try:
        user_id = user_id.strip('"')  # retire les guillemets accidentels
        return await user_service.update_user_rating(user_id,rating_data.rating)
    except Exception as e:
        handle_exception(e)

@admin_router.get(
    "/{user_id}/exists",
    response_model=UserExistsResponseSchema,  # Schema avec champ 'exists'
    status_code=status.HTTP_200_OK,
    summary="Vérifier l'existence",
    description="Vérifie si un utilisateur existe",
    dependencies=[Depends(require_admin)]
)
async def user_exists(user_id: str):
    try:
        user_id = user_id.strip('"')  # retire les guillemets accidentels
        return  await user_service.user_exists(user_id)
    except Exception as e:
        handle_exception(e)

@admin_router.get(
    "/stats/count",
    response_model=UserCountResponseSchema,  # Schema avec champ 'count'
    status_code=status.HTTP_200_OK,
    summary="Nombre d'utilisateurs",
    description="Retourne le nombre total d'utilisateurs avec filtres optionnels",
    dependencies=[Depends(require_admin)]
)
async def get_users_count(is_active: Optional[bool] = Query(None)):
    try:
        return await user_service.get_users_count(is_active)
    except Exception as e:
        handle_exception(e)

# --------------------------------------
# Récupérer tous les utilisateurs
# --------------------------------------

@admin_router.get("/all", response_model=List[UserOutSchema],dependencies=[Depends(require_admin)])
async def get_all_users(limit: int = 100, offset: int = 0):
    try:
        return await user_service.get_all_users(limit=limit, offset=offset)
    except Exception as e:
        handle_exception(e)

# --------------------------------------
# Suppression d’un utilisateur
# --------------------------------------

@admin_router.delete("/{user_id}",response_model=DeleteResponseSchema,status_code=status.HTTP_200_OK,dependencies=[Depends(require_admin)])
async def delete_user(user_id: str):
    try:
        user_id = user_id.strip('"')  # retire les guillemets accidentels
        return await user_service.delete_user(user_id)
    except Exception as e:
        handle_exception(e)


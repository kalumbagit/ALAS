from typing import Optional, List, Dict, Any
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, Body,status
from pydantic import ValidationError

from core.logging import logger
from schemas.category_schemas import (
    CategoryCreate,
    CategoryUpdate,
    ResponseSchema
)
from schemas.filter_schemas import (
    PaginationSchema,
    CategoryQuerySchema
)
from services.category_service import CategoryService
from core.dependencies import (
    get_pagination_params,
    validate_merchant_access,
    get_category_query_params,
    get_category_id
)
from core.exceptions import (
    NotFoundException,
    ConflictException,
    InternalServerException,
    UnauthorizedException,
    APIException
)
from middlewares.auth_middleware import get_current_user,get_current_admin,get_current_merchant

router = APIRouter(prefix="/categories", tags=["categories"])

# ============================
# 🔹 UTILITAIRES 
# ============================
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

def get_user_id_or_raise(user):
    if isinstance(user, dict):
        user_id = user.get("user_id")
    else:
        user_id = getattr(user, "user_id", None)

    if user_id is None:
        raise UnauthorizedException(detail="Utilisateur inconnu")
    return user_id

def get_user_type_or_raise(user):
    if isinstance(user, dict):
        user_type = user.get("user_type")
    else:
        user_type = getattr(user, "user_type", None)
    
    if not user_type:
        raise UnauthorizedException(detail="Utilisateur inconnu")
    
    return user_type

# ============================
# 🔹 ROUTES CRUD BASIQUES
# ============================

@router.post("", response_model=ResponseSchema, status_code=201)
async def create_category(
    payload: CategoryCreate,
    current_user = Depends(get_current_user),
    return_data: bool = Query(False, description="Inclure les données créées dans la réponse")
):
    """
    Crée une nouvelle catégorie
    """
    try:
        user_id = get_user_id_or_raise(current_user)
        payload.merchant_id=user_id
        return await CategoryService.create_category(
            payload=payload,
            return_data=return_data
        )
    except Exception as e:
        handle_exception(e)

@router.get("/{category_id}", response_model=ResponseSchema)
async def get_category(
    category_id: UUID,
    current_user = Depends(get_current_user),
    include_children: bool = Query(False, description="Inclure les sous-catégories")
):
    """
    Récupère une catégorie par son ID
    """
    try:
        
        return await CategoryService.get_category(
            category_id=category_id,
            include_children=include_children
        )
    except Exception as e:
        handle_exception(e)

@router.get("", response_model=ResponseSchema)
async def list_categories(
    query_params: CategoryQuerySchema = Depends(get_category_query_params),
    current_user = Depends(get_current_user)
):
    """
    Liste les catégories avec pagination et filtres avancés
    """
    # Application des filtres spécifiques au marchand si nécessaire
    user_type=get_user_type_or_raise(current_user)
    if user_type =="merchant":
        merchant_id=get_user_id_or_raise(current_user)
    else:
        merchant_id =None
    try:
        
        return await CategoryService.list_categories(
            merchant_id=merchant_id,
            include_global=query_params.filters.include_global,
            include_inactive=query_params.filters.include_inactive,
            only_with_products=query_params.filters.only_with_products,
            pagination=query_params.pagination
        )
    except Exception as e:
        handle_exception(e)

@router.patch("/{category_id}", response_model=ResponseSchema)
async def update_category(
    payload: CategoryUpdate,
    category_id: UUID = Depends(get_category_id),
    current_user = Depends(get_current_user),
    return_data: bool = Query(False, description="Inclure les données mises à jour dans la réponse")
):
    """
    Met à jour une catégorie
    """
    try:
        user_type=get_user_type_or_raise(current_user)
        if user_type =="merchant":
            merchant_id=get_user_id_or_raise(current_user)
        else:
            merchant_id =None
        
        return await CategoryService.update_category(
            category_id=category_id,
            payload=payload,
            updated_by=merchant_id,
            return_data=return_data
        )
    except Exception as e:
        handle_exception(e)

@router.delete("/{category_id}", response_model=ResponseSchema)
async def delete_category(
    category_id: UUID = Depends(get_category_id),
    force: bool = Query(False, description="Forcer la suppression malgré les dépendances"),
    current_user = Depends(get_current_user)
):
    """
    Supprime une catégorie (soft delete)
    """
    try:
        
        return await CategoryService.delete_category(
            category_id=category_id,
            force=force
        )
    except Exception as e:
        handle_exception(e)

# ============================
# 🔹 ROUTES AVANCÉES
# ============================

@router.get("/{category_id}/products", response_model=ResponseSchema)
async def get_category_with_products(
    category_id: UUID = Depends(get_category_id),
    include_inactive: bool = Query(False, description="Inclure les produits inactifs"),
    pagination: PaginationSchema = Depends(get_pagination_params),
    current_user = Depends(get_current_user)
):
    """
    Récupère une catégorie avec ses produits paginés
    """
    try:
        # Application des filtres spécifiques au marchand si nécessaire
        user_type=get_user_type_or_raise(current_user)
        if user_type =="merchant":
            merchant_id=get_user_id_or_raise(current_user)
        else:
            merchant_id =None
        
        return await CategoryService.list_categories_with_products(
            merchant_id=merchant_id,
            include_inactive_products=include_inactive,
            pagination=pagination
        )
    except Exception as e:
        handle_exception(e)

@router.get("/tree/hierarchy", response_model=ResponseSchema)
async def get_category_tree(
    include_global: bool = Query(True, description="Inclure les catégories globales"),
    current_user = Depends(get_current_user)
):
    """
    Récupère l'arborescence complète des catégories
    """
    try:
        
        # Si merchant_id n'est pas fourni, utiliser celui de l'utilisateur connecté
        # Application des filtres spécifiques au marchand si nécessaire
        user_type=get_user_type_or_raise(current_user)
        if user_type =="merchant":
            merchant_id=get_user_id_or_raise(current_user)
        else:
            merchant_id =None
        
        return await CategoryService.get_category_tree(
            merchant_id=merchant_id,
            include_global=include_global
        )
    except Exception as e:
        handle_exception(e)

@router.get("/search/global", response_model=ResponseSchema)
async def search_categories(
    query: str = Query(..., min_length=2, description="Terme de recherche (min. 2 caractères)"),
    merchant_id: Optional[UUID] = Query(None, description="Restreindre la recherche à un marchand"),
    limit: int = Query(20, ge=1, le=50, description="Nombre maximum de résultats"),
    current_user: UUID = Depends(get_current_user)
):
    """
    Recherche globale de catégories par nom ou description
    """
    try:
        
        if merchant_id is None:
            merchant_id = await validate_merchant_access(current_user)
        
        return await CategoryService.search_categories(
            query=query,
            merchant_id=merchant_id,
            limit=limit
        )
    except Exception as e:
        handle_exception(e)

@router.get("/stats/overview", response_model=ResponseSchema)
async def get_categories_stats(
    merchant_id: Optional[UUID] = Query(None, description="ID du marchand pour les statistiques"),
    current_user: UUID = Depends(get_current_user)
):
    """
    Récupère les statistiques des catégories
    """
    try:
        
        if merchant_id is None:
            merchant_id = await validate_merchant_access(current_user)
        
        return await CategoryService.get_categories_stats(merchant_id=merchant_id)
    except Exception as e:
        handle_exception(e)

# ============================
# 🔹 ROUTES ADMIN/OPERATIONS EN LOT
# ============================

@router.post("/bulk/update", response_model=ResponseSchema)
async def bulk_update_categories(
    updates: List[Dict[str, Any]] = Body(..., description="Liste des mises à jour"),
    current_user: UUID = Depends(get_current_user)
):
    """
    Met à jour plusieurs catégories en une seule opération (ADMIN)
    """
    try:
        
        # Validation des permissions admin
        await _validate_admin_access(current_user)
        
        return await CategoryService.bulk_update_categories(
            updates=updates,
            updated_by=current_user
        )
    except Exception as e:
        handle_exception(e)

@router.post("/{category_id}/restore", response_model=ResponseSchema)
async def restore_category(
    category_id: UUID = Depends(get_category_id),
    current_user: UUID = Depends(get_current_user)
):
    """
    Restaure une catégorie précédemment supprimée (ADMIN)
    """
    try:
        
        # Validation des permissions admin
        await _validate_admin_access(current_user)
        
        return await CategoryService.restore_category(category_id=category_id)
    except Exception as e:
        handle_exception(e)

@router.get("/admin/inactive", response_model=ResponseSchema)
async def list_inactive_categories(
    pagination: PaginationSchema = Depends(get_pagination_params),
    current_user: UUID = Depends(get_current_user)
):
    """
    Liste les catégories inactives (ADMIN)
    """
    try:
        
        # Validation des permissions admin
        await _validate_admin_access(current_user)
        
        return await CategoryService.list_categories(
            include_inactive=True,
            only_with_products=False,
            pagination=pagination
        )
    except Exception as e:
        handle_exception(e)

# ============================
# 🔹 UTILITAIRES INTERNES
# ============================

async def _validate_admin_access(user_id: UUID) -> bool:
    """
    Valide que l'utilisateur a les droits d'administration
    """
    try:
        
        # Implémentation dépendante de ton système d'authentification
        # Pour l'exemple, on suppose une fonction exists dans les dépendances
        from core.dependencies import is_admin_user
        if not await is_admin_user(user_id):
            raise HTTPException(
                status_code=403,
                detail="Permissions administrateur requises"
            )
        return True
    except Exception as e:
        handle_exception(e)

# ============================
# 🔹 ROUTES UTILITAIRES
# ============================

@router.get("/export/formats")
async def get_export_formats():
    """
    Retourne les formats d'export disponibles
    """
    try:
        
        return {
            "formats": ["json", "csv", "excel"],
            "default": "json",
            "max_records": 10000
        }
    except Exception as e:
        handle_exception(e)
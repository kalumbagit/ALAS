from typing import Optional,List
from uuid import UUID
from fastapi import Query, Depends,Path
from schemas.filter_schemas import PaginationSchema, CategoryFilterSchema,ProductQuerySchema,ProductFilterSchema,CategoryQuerySchema
from core.exceptions import APIException


async def get_pagination_params(
    page: int = Query(1, ge=1, description="Numéro de page"),
    page_size: int = Query(20, ge=1, le=100, description="Taille de la page"),
    sort_by: str = Query("created_at", description="Champ de tri"),
    sort_order: str = Query("desc", description="Ordre de tri")
) -> PaginationSchema:
    """Dépendance pour les paramètres de pagination standardisés"""
    return PaginationSchema(
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=sort_order
    )

async def get_category_filters(
    search: Optional[str] = Query(None, description="Recherche par nom ou description"),
    merchant_id: Optional[UUID] = Query(None, description="Filtrer par marchand"),
    include_global: bool = Query(True, description="Inclure les catégories globales"),
    include_inactive: bool = Query(False, description="Inclure les catégories inactives"),
    only_with_products: bool = Query(False, description="Catégories avec produits seulement"),
    parent_id: Optional[UUID] = Query(None, description="Catégories enfants d'un parent")
) -> CategoryFilterSchema:
    """Dépendance pour les filtres de catégories"""
    return CategoryFilterSchema(
        search=search,
        merchant_id=merchant_id,
        include_global=include_global,
        include_inactive=include_inactive,
        only_with_products=only_with_products,
        parent_id=parent_id
    )

async def get_current_user() -> UUID:
    """
    Récupère l'utilisateur connecté depuis le token JWT
    À adapter selon ton système d'authentification
    """
    # Implémentation factice - à remplacer par ta logique réelle
    return UUID("12345678-1234-1234-1234-123456789abc")

async def validate_merchant_access(user_id: UUID) -> Optional[UUID]:
    """
    Valide l'accès marchand et retourne le merchant_id
    À adapter selon ta logique métier
    """
    # Implémentation factice
    return None  # ou le merchant_id spécifique

async def is_admin_user(user_id: UUID) -> bool:
    """
    Vérifie si l'utilisateur a des droits administrateur
    """
    # Implémentation factice
    return False

async def get_product_filters(
    search: Optional[str] = Query(None, description="Recherche texte"),
    category_id: Optional[UUID] = Query(None, description="Filtrer par catégorie"),
    category_ids: Optional[List[UUID]] = Query(None, description="Filtrer par plusieurs catégories"),
    min_price: Optional[float] = Query(None, ge=0, description="Prix minimum"),
    max_price: Optional[float] = Query(None, ge=0, description="Prix maximum"),
    currency: Optional[str] = Query(None, description="Devise spécifique"),
    in_stock: Optional[bool] = Query(None, description="Produits en stock seulement"),
    low_stock: Optional[bool] = Query(None, description="Produits en stock faible"),
    has_discount: Optional[bool] = Query(None, description="Produits en promotion"),
    tags: Optional[List[str]] = Query(None, description="Filtrer par tags"),
    is_available: Optional[bool] = Query(True, description="Produits disponibles"),
    is_active: Optional[bool] = Query(True, description="Produits actifs")
):
    """Dépendance pour les filtres de produits"""
    return ProductFilterSchema(
        search=search,
        category_id=category_id,
        category_ids=category_ids,
        min_price=min_price,
        max_price=max_price,
        currency=currency,
        in_stock=in_stock,
        low_stock=low_stock,
        has_discount=has_discount,
        tags=tags,
        is_available=is_available,
        is_active=is_active
    )

async def get_product_query_params(
    pagination: PaginationSchema = Depends(get_pagination_params),
    search: Optional[str] = Query(None, description="Recherche texte"),
    category_id: Optional[UUID] = Query(None, description="Filtrer par catégorie"),
    category_ids: Optional[List[UUID]] = Query(None, description="Filtrer par plusieurs catégories"),
    min_price: Optional[float] = Query(None, ge=0, description="Prix minimum"),
    max_price: Optional[float] = Query(None, ge=0, description="Prix maximum"),
    currency: Optional[str] = Query(None, description="Devise spécifique"),
    in_stock: Optional[bool] = Query(None, description="Produits en stock seulement"),
    low_stock: Optional[bool] = Query(None, description="Produits en stock faible"),
    has_discount: Optional[bool] = Query(None, description="Produits en promotion"),
    tags: Optional[List[str]] = Query(None, description="Filtrer par tags"),
    is_available: Optional[bool] = Query(True, description="Produits disponibles"),
    is_active: Optional[bool] = Query(True, description="Produits actifs")
) -> ProductQuerySchema:
    """Combine pagination et filtres pour les requêtes produits"""
    filters = ProductFilterSchema(
        search=search,
        category_id=category_id,
        category_ids=category_ids,
        min_price=min_price,
        max_price=max_price,
        currency=currency,
        in_stock=in_stock,
        low_stock=low_stock,
        has_discount=has_discount,
        tags=tags,
        is_available=is_available,
        is_active=is_active
    )
    return ProductQuerySchema(pagination=pagination, filters=filters)

async def get_category_query_params(
    pagination: PaginationSchema = Depends(get_pagination_params),
    filters: CategoryFilterSchema = Depends(get_category_filters)
) -> CategoryQuerySchema:
    """Combine pagination et filtres pour les requêtes catégories"""
    return CategoryQuerySchema(pagination=pagination, filters=filters)

async def get_category_id(category_id: UUID = Path(..., description="ID de la catégorie")) -> UUID:
    """Validation de base pour l'ID de catégorie"""
    if not category_id:
        raise APIException(detail="ID de catégorie requis")
    return category_id

async def get_product_id(product_id: UUID = Path(..., description="ID du produit")) -> UUID:
    """Validation de base pour l'ID de produit"""
    if not product_id:
        raise APIException(detail="ID de produit requis")
    return product_id
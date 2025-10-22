from typing import Optional, List, Dict, Any
from uuid import UUID
from fastapi import APIRouter, Depends, Query, Body

from schemas.product_schemas import ProductCreate,ProductUpdate
from schemas.category_schemas import ResponseSchema
from schemas.filter_schemas import (
    PaginationSchema,
    ProductFilterSchema,
    ProductQuerySchema,
    DateRangeFilterSchema
)
from services.product_service import ProductService

# Import des utilitaires depuis le contrôleur catégorie
from .category_controller import (
    handle_exception,
    get_pagination_params,
    get_category_id,
    _validate_admin_access
)
from core.dependencies import (
    get_current_user,
    validate_merchant_access,
    get_product_query_params,
    get_product_id
)


router = APIRouter(prefix="/products", tags=["products"])


# ============================
# 🔹 ROUTES CRUD BASIQUES
# ============================

@router.post("", response_model=ResponseSchema, status_code=201)
async def create_product(
    payload: ProductCreate,
    current_user: UUID = Depends(get_current_user),
    return_data: bool = Query(False, description="Inclure les données créées dans la réponse")
):
    """
    Crée un nouveau produit
    """
    try:

        return await ProductService.create_product(
            user_id=current_user,
            payload=payload,
            return_data=return_data
        )
    except Exception as e: 
        handle_exception(e)

@router.get("/{product_id}", response_model=ResponseSchema)
async def get_product(
    product_id: UUID = Depends(get_product_id),
    include_category: bool = Query(True, description="Inclure les données de la catégorie"),
    include_analytics: bool = Query(False, description="Inclure les données analytiques"),
    current_user: UUID = Depends(get_current_user)
):
    """
    Récupère un produit par son ID
    """
    try:
        
        return await ProductService.get_product(
            product_id=product_id,
            include_category=include_category,
            include_analytics=include_analytics
        )
    except Exception as e: 
        handle_exception(e)

@router.get("", response_model=ResponseSchema)
async def list_products(
    query_params: ProductQuerySchema = Depends(get_product_query_params),
    current_user: UUID = Depends(get_current_user)
):
    """
    Liste les produits avec pagination et filtres avancés
    """
    try:
        
        # Pour les utilisateurs normaux, on restreint à leurs produits
        merchant_id = await validate_merchant_access(current_user)
        user_id = current_user if not merchant_id else None
        
        return await ProductService.list_products(
            query_params=query_params,
            user_id=user_id
        )
    except Exception as e: 
        handle_exception(e)

@router.put("/{product_id}", response_model=ResponseSchema)
async def update_product(
    payload: ProductUpdate,
    product_id: UUID = Depends(get_product_id),
    current_user: UUID = Depends(get_current_user),
    return_data: bool = Query(False, description="Inclure les données mises à jour dans la réponse")
):
    """
    Met à jour un produit
    """
    try:
        
        return await ProductService.update_product(
            product_id=product_id,
            payload=payload,
            updated_by=current_user,
            return_data=return_data
        )
    except Exception as e: 
        handle_exception(e)

@router.delete("/{product_id}", response_model=ResponseSchema)
async def delete_product(
    product_id: UUID = Depends(get_product_id),
    current_user: UUID = Depends(get_current_user)
):
    """
    Supprime un produit (soft delete)
    """
    try:
        
        return await ProductService.delete_product(product_id=product_id)
    except Exception as e: 
        handle_exception(e)

# ============================
# 🔹 ROUTES GESTION DU STOCK
# ============================

@router.patch("/{product_id}/stock", response_model=ResponseSchema)
async def update_stock(
    product_id: UUID = Depends(get_product_id),
    new_stock: int = Body(..., ge=0, description="Nouvelle quantité en stock"),
    reason: str = Body("manual_update", description="Raison de la mise à jour"),
    current_user: UUID = Depends(get_current_user)
):
    """
    Met à jour le stock d'un produit
    """
    try:
        
        return await ProductService.update_stock(
            product_id=product_id,
            new_stock=new_stock,
            reason=reason
        )
    except Exception as e: 
        handle_exception(e)

@router.patch("/{product_id}/stock/increase", response_model=ResponseSchema)
async def increase_stock(
    product_id: UUID = Depends(get_product_id),
    quantity: int = Body(..., gt=0, description="Quantité à ajouter"),
    reason: str = Body("restock", description="Raison de l'augmentation"),
    current_user: UUID = Depends(get_current_user)
):
    """
    Augmente le stock d'un produit
    """
    try:
        
        return await ProductService.increase_stock(
            product_id=product_id,
            quantity=quantity,
            reason=reason
        )
    except Exception as e: 
        handle_exception(e)

@router.patch("/{product_id}/stock/decrease", response_model=ResponseSchema)
async def decrease_stock(
    product_id: UUID = Depends(get_product_id),
    quantity: int = Body(..., gt=0, description="Quantité à retirer"),
    reason: str = Body("sale", description="Raison de la diminution"),
    current_user: UUID = Depends(get_current_user)
):
    """
    Diminue le stock d'un produit
    """
    try:
        
        return await ProductService.decrease_stock(
            product_id=product_id,
            quantity=quantity,
            reason=reason
        )
    except Exception as e: 
        handle_exception(e)

@router.post("/stock/bulk-update", response_model=ResponseSchema)
async def bulk_update_stock(
    updates: List[Dict[str, Any]] = Body(..., description="Liste des mises à jour de stock"),
    reason: str = Body("bulk_update", description="Raison de la mise à jour en lot"),
    current_user: UUID = Depends(get_current_user)
):
    """
    Met à jour le stock de plusieurs produits en une opération
    """
    try:
        
        return await ProductService.bulk_update_stock(
            updates=updates,
            reason=reason
        )
    except Exception as e: 
        handle_exception(e)

# ============================
# 🔹 ROUTES RECHERCHE ET ANALYTICS
# ============================

@router.get("/search/global", response_model=ResponseSchema)
async def search_products(
    query: str = Query(..., min_length=2, description="Terme de recherche (min. 2 caractères)"),
    limit: int = Query(20, ge=1, le=50, description="Nombre maximum de résultats"),
    current_user: UUID = Depends(get_current_user)
):
    """
    Recherche globale de produits
    """
    try:
        
        return await ProductService.search_products(
            search_term=query,
            user_id=current_user,
            limit=limit
        )
    except Exception as e: 
        handle_exception(e)

@router.get("/analytics/overview", response_model=ResponseSchema)
async def get_products_stats(
    current_user: UUID = Depends(get_current_user),
    start_date: Optional[str] = Query(None, description="Date de début (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="Date de fin (YYYY-MM-DD)")
):
    """
    Récupère les statistiques des produits
    """

    try:
        
        date_range = None
        if start_date or end_date:
            date_range = DateRangeFilterSchema(
                start_date=start_date,
                end_date=end_date
            )
        
        return await ProductService.get_products_stats(
            user_id=current_user,
            date_range=date_range
        )
    except Exception as e: 
        handle_exception(e)

@router.get("/alerts/low-stock", response_model=ResponseSchema)
async def get_low_stock_products(
    threshold: int = Query(5, ge=1, description="Seuil d'alerte stock faible"),
    current_user: UUID = Depends(get_current_user)
):
    """
    Liste les produits avec stock faible
    """
    try:
        
        return await ProductService.get_low_stock_products(
            threshold=threshold,
            user_id=current_user
        )
    except Exception as e: 
        handle_exception(e)

# ============================
# 🔹 ROUTES GESTION DISPONIBILITÉ
# ============================

@router.patch("/{product_id}/availability", response_model=ResponseSchema)
async def toggle_availability(
    product_id: UUID = Depends(get_product_id),
    current_user: UUID = Depends(get_current_user)
):
    """
    Active/désactive la disponibilité d'un produit
    """
    try:
        
        return await ProductService.toggle_availability(product_id=product_id)
    except Exception as e: 
        handle_exception(e)

@router.post("/bulk/availability", response_model=ResponseSchema)
async def bulk_toggle_availability(
    product_ids: List[UUID] = Body(..., description="Liste des IDs de produits"),
    make_available: bool = Body(..., description="True pour activer, False pour désactiver"),
    current_user: UUID = Depends(get_current_user)
):
    """
    Active/désactive plusieurs produits en une opération
    """
    try:
        
        operations = [
            {
                "product_id": pid,
                "operation": "activate" if make_available else "deactivate"
            }
            for pid in product_ids
        ]
        
        return await ProductService.bulk_operations(
            operations=operations,
            user_id=current_user
        )
    except Exception as e: 
        handle_exception(e)

# ============================
# 🔹 ROUTES ADMIN/OPERATIONS EN LOT
# ============================

@router.post("/bulk/operations", response_model=ResponseSchema)
async def bulk_operations(
    operations: List[Dict[str, Any]] = Body(..., description="Liste des opérations à effectuer"),
    current_user: UUID = Depends(get_current_user)
):
    """
    Exécute plusieurs opérations sur les produits en une requête (ADMIN)
    """
    try:
        
        # Validation des permissions admin
        await _validate_admin_access(current_user)
        
        return await ProductService.bulk_operations(
            operations=operations,
            user_id=current_user
        )
    except Exception as e: 
        handle_exception(e)

@router.post("/{product_id}/restore", response_model=ResponseSchema)
async def restore_product(
    product_id: UUID = Depends(get_product_id),
    current_user: UUID = Depends(get_current_user)
):
    """
    Restaure un produit précédemment supprimé (ADMIN)
    """
    try:
        
        
        # Validation des permissions admin
        await _validate_admin_access(current_user)
        
        # Note: Tu devras ajouter cette méthode dans ProductService
        return await ProductService.restore_product(product_id=product_id)
    except Exception as e: 
        handle_exception(e)

@router.get("/admin/inactive", response_model=ResponseSchema)
async def list_inactive_products(
    pagination: PaginationSchema = Depends(get_pagination_params),
    current_user: UUID = Depends(get_current_user)
):
    """
    Liste les produits inactifs (ADMIN)
    """
    try:
        
        # Validation des permissions admin
        await _validate_admin_access(current_user)
        
        query_params = ProductQuerySchema(
            pagination=pagination,
            filters=ProductFilterSchema(is_active=False)
        )
        
        return await ProductService.list_products(query_params=query_params)
    except Exception as e: 
        handle_exception(e)

# ============================
# 🔹 ROUTES SPÉCIALISÉES
# ============================

@router.get("/category/{category_id}", response_model=ResponseSchema)
async def get_products_by_category(
    category_id: UUID = Depends(get_category_id),
    pagination: PaginationSchema = Depends(get_pagination_params),
    only_available: bool = Query(True, description="Produits disponibles seulement"),
    current_user: UUID = Depends(get_current_user)
):
    """
    Récupère les produits d'une catégorie spécifique
    """
    try:
        
        query_params = ProductQuerySchema(
            pagination=pagination,
            filters=ProductFilterSchema(
                category_id=category_id,
                is_available=only_available
            )
        )
        
        merchant_id = await validate_merchant_access(current_user)
        user_id = current_user if not merchant_id else None
        
        return await ProductService.list_products(
            query_params=query_params,
            user_id=user_id
        )
    except Exception as e: 
        handle_exception(e)

@router.get("/featured/promotions", response_model=ResponseSchema)
async def get_featured_promotions(
    limit: int = Query(10, ge=1, le=20, description="Nombre de produits en promotion"),
    current_user: UUID = Depends(get_current_user)
):
    """
    Récupère les produits en promotion
    """
    try:
        
        query_params = ProductQuerySchema(
            pagination=PaginationSchema(page=1, page_size=limit),
            filters=ProductFilterSchema(
                has_discount=True,
                is_available=True,
                is_active=True
            )
        )
        
        merchant_id = await validate_merchant_access(current_user)
        user_id = current_user if not merchant_id else None
        
        return await ProductService.list_products(
            query_params=query_params,
            user_id=user_id
        )
    except Exception as e: 
        handle_exception(e)

@router.get("/user/own", response_model=ResponseSchema)
async def get_user_products(
    query_params: ProductQuerySchema = Depends(get_product_query_params),
    current_user: UUID = Depends(get_current_user)
):
    """
    Récupère les produits de l'utilisateur connecté
    """
    try:
        
        return await ProductService.list_products(
            query_params=query_params,
            user_id=current_user
        )
    except Exception as e: 
        handle_exception(e)

# ============================
# 🔹 ROUTES UTILITAIRES
# ============================


@router.get("/export/formats")
async def get_export_formats():
    """
    Retourne les formats d'export disponibles pour les produits
    """
    try:
        
        return {
            "formats": ["json", "csv", "excel"],
            "default": "json",
            "max_records": 10000,
            "available_fields": [
                "id", "name", "description", "price", "currency", 
                "stock_quantity", "is_available", "sku", "tags"
            ]
        }
    except Exception as e: 
        handle_exception(e)

# ============================
# 🔹 ROUTES RAPPORTS AVANCÉS
# ============================

@router.get("/reports/stock-levels", response_model=ResponseSchema)
async def get_stock_levels_report(
    threshold: int = Query(5, description="Seuil pour stock faible"),
    current_user: UUID = Depends(get_current_user)
):
    """
    Génère un rapport détaillé des niveaux de stock
    """
    try:
        
        # Récupérer les statistiques générales
        stats_response = await ProductService.get_products_stats(user_id=current_user)
        
        # Récupérer les alertes stock faible
        low_stock_response = await ProductService.get_low_stock_products(
            threshold=threshold,
            user_id=current_user
        )
        
        # Combiner les données
        report_data = {
            "summary": stats_response.data.get("stats", {}),
            "low_stock_alerts": low_stock_response.data.get("low_stock_products", [])
        }
        
        return ResponseSchema(
            success=True,
            message="Rapport des niveaux de stock généré avec succès",
            data=report_data
        )
    except Exception as e: 
        handle_exception(e)
    

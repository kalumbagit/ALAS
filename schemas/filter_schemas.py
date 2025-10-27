from typing import Optional, List, Dict, Any, Generic, TypeVar
from pydantic import BaseModel, Field, field_validator
from enum import Enum

# Type générique pour la pagination
T = TypeVar('T')

class SortOrderEnum(str, Enum):
    """Enum pour l'ordre de tri"""
    ASC = "asc"
    DESC = "desc"

class PaginationSchema(BaseModel):
    """
    Schéma standard pour la pagination des requêtes
    """
    page: int = Field(
        default=1, 
        ge=1, 
        description="Numéro de page (commence à 1)",
        example=1
    )
    
    page_size: int = Field(
        default=20, 
        ge=1, 
        le=100, 
        description="Nombre d'éléments par page (1-100)",
        example=20
    )
    
    sort_by: Optional[str] = Field(
        default="created_at",
        description="Champ de tri",
        example="name"
    )
    
    sort_order: SortOrderEnum = Field(
        default=SortOrderEnum.DESC,
        description="Ordre de tri (ascendant ou descendant)"
    )
    
    search: Optional[str] = Field(
        default=None,
        description="Terme de recherche global",
        example="pizza"
    )

    model_config = {"from_attributes": True}

    @field_validator('page_size')
    def validate_page_size(cls, v):
        """Valide que la taille de page est raisonnable"""
        if v > 100:
            raise ValueError("La taille de page ne peut pas dépasser 100")
        return v

    @property
    def offset(self) -> int:
        """Calcule l'offset pour les requêtes SQL"""
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        """Retourne la limite pour les requêtes SQL"""
        return self.page_size

class PaginatedResponse( Generic[T]):
    """
    Réponse paginée standardisée
    """
    success: bool = True
    message: str
    data: List[T]
    pagination: Dict[str, Any] = Field(
        description="Informations de pagination"
    )

    model_config = {"from_attributes": True}

    @classmethod
    def create(
        cls,
        data: List[T],
        total: int,
        pagination: PaginationSchema,
        message: str = "Données récupérées avec succès"
    ) -> 'PaginatedResponse[T]':
        """Factory method pour créer une réponse paginée"""
        total_pages = (total + pagination.page_size - 1) // pagination.page_size
        
        
        pagination_info = {
            "page": pagination.page,
            "page_size": pagination.page_size,
            "total": total,
            "total_pages": total_pages,
            "has_previous": pagination.page > 1,
            "has_next": pagination.page < total_pages
        }
        
        return cls(
            message=message,
            data=data,
            pagination=pagination_info
        )

# ============================
# 🔹 SCHÉMAS DE FILTRES AVANCÉS
# ============================

class ProductFilterSchema(BaseModel):
    """
    Filtres avancés pour les produits
    """
    search: Optional[str] = Field(None, description="Recherche texte (nom, description)")
    category_id: Optional[str] = Field(None, description="Filtrer par catégorie")
    category_ids: Optional[List[str]] = Field(None, description="Filtrer par plusieurs catégories")
    min_price: Optional[float] = Field(None, ge=0, description="Prix minimum")
    max_price: Optional[float] = Field(None, ge=0, description="Prix maximum")
    currency: Optional[str] = Field(None, description="Devise spécifique")
    in_stock: Optional[bool] = Field(None, description="Produits en stock seulement")
    low_stock: Optional[bool] = Field(None, description="Produits en stock faible")
    has_discount: Optional[bool] = Field(None, description="Produits en promotion")
    tags: Optional[List[str]] = Field(None, description="Filtrer par tags")
    merchant_id: Optional[str] = Field(None, description="Filtrer par marchand")
    is_available: Optional[bool] = Field(True, description="Produits disponibles")
    is_active: Optional[bool] = Field(True, description="Produits actifs")

    model_config = {"from_attributes": True}

    @field_validator('max_price')
    def validate_price_range(cls, v, values):
        """Valide que max_price >= min_price"""
        if v is not None and 'min_price' in values and values['min_price'] is not None:
            if v < values['min_price']:
                raise ValueError('max_price doit être supérieur ou égal à min_price')
        return v

class CategoryFilterSchema(BaseModel):
    """
    Filtres avancés pour les catégories
    """
    search: Optional[str] = Field(None, description="Recherche par nom ou description")
    merchant_id: Optional[str] = Field(None, description="Filtrer par marchand")
    include_global: bool = Field(True, description="Inclure les catégories globales")
    include_inactive: bool = Field(False, description="Inclure les catégories inactives")
    only_with_products: bool = Field(False, description="Catégories avec produits seulement")
    parent_id: Optional[str] = Field(
        None, 
        description="Catégories enfants d'une catégorie parente spécifique"
    )
    is_active: Optional[bool] = Field(True, description="Catégories actives seulement")

    model_config = {"from_attributes": True}

class DateRangeFilterSchema(BaseModel):
    """
    Filtre par plage de dates
    """
    start_date: Optional[str] = Field(
        None, 
        description="Date de début (format: YYYY-MM-DD)",
        example="2024-01-01"
    )
    end_date: Optional[str] = Field(
        None, 
        description="Date de fin (format: YYYY-MM-DD)",
        example="2024-12-31"
    )
    date_field: str = Field(
        default="created_at",
        description="Champ de date à filtrer",
        example="created_at"
    )

    model_config = {
        "from_attributes": True,
        "extra": "forbid"  # empêche les champs inconnus
    }

    @field_validator('end_date')
    def validate_date_range(cls, v, info):
        """Valide que end_date >= start_date"""
        start_date = info.data.get('start_date')
        if v is not None and start_date is not None:
            if v < start_date:
                raise ValueError('end_date doit être postérieure à start_date')
        return v

# ============================
# 🔹 SCHÉMAS COMBINÉS
# ============================

class ProductQuerySchema(BaseModel):
    """
    Schéma combiné pour les requêtes produits
    """
    pagination: PaginationSchema = Field(default_factory=PaginationSchema)
    filters: ProductFilterSchema = Field(default_factory=ProductFilterSchema)
    date_range: Optional[DateRangeFilterSchema] = Field(None)

    model_config = {"from_attributes": True}

class CategoryQuerySchema(BaseModel):
    """
    Schéma combiné pour les requêtes catégories
    """
    pagination: PaginationSchema = Field(default_factory=PaginationSchema)
    filters: CategoryFilterSchema = Field(default_factory=CategoryFilterSchema)

    model_config = {"from_attributes": True}

# ============================
# 🔹 RÉPONSES STANDARDISÉES
# ============================

class FilterMetadata(BaseModel):
    """
    Métadonnées pour les réponses filtrées
    """
    applied_filters: Dict[str, Any] = Field(default_factory=dict)
    total_before_filtering: Optional[int] = Field(None, description="Total avant application des filtres")
    search_query: Optional[str] = Field(None, description="Terme de recherche appliqué")

    model_config = {"from_attributes": True}

class EnhancedPaginatedResponse( Generic[T]):
    """
    Réponse paginée enrichie avec métadonnées de filtrage
    """
    success: bool = True
    message: str
    data: List[T]
    pagination: Dict[str, Any]
    filters: Optional[FilterMetadata] = Field(None, description="Métadonnées des filtres appliqués")

    model_config = {"from_attributes": True}

    @classmethod
    def create(
        cls,
        data: List[T],
        total: int,
        pagination: PaginationSchema,
        message: str = "Données récupérées avec succès",
        filters: Optional[FilterMetadata] = None
    ) -> 'EnhancedPaginatedResponse[T]':
        """Factory method pour créer une réponse paginée enrichie"""
        total_pages = (total + pagination.page_size - 1) // pagination.page_size
        
        pagination_info = {
            "page": pagination.page,
            "page_size": pagination.page_size,
            "total": total,
            "total_pages": total_pages,
            "has_previous": pagination.page > 1,
            "has_next": pagination.page < total_pages
        }
        
        return cls(
            message=message,
            data=data,
            pagination=pagination_info,
            filters=filters
        )

# ============================
# 🔹 UTILITAIRES
# ============================

class ExportOptionsSchema(BaseModel):
    """
    Options pour l'export de données
    """
    format: str = Field(default="json", description="Format d'export: json, csv, excel")
    include_inactive: bool = Field(default=False, description="Inclure les éléments inactifs")
    columns: Optional[List[str]] = Field(None, description="Colonnes spécifiques à exporter")
    date_range: Optional[DateRangeFilterSchema] = Field(None, description="Plage de dates pour l'export")

    model_config = {"from_attributes": True}

class BulkOperationSchema(BaseModel):
    """
    Schéma pour les opérations en lot
    """
    ids: List[str] = Field(..., description="Liste des IDs à traiter")
    operation: str = Field(..., description="Type d'opération: activate, deactivate, delete")
    
    model_config = {"from_attributes": True}

    @field_validator('operation')
    def validate_operation(cls, v):
        """Valide le type d'opération"""
        allowed_operations = ['activate', 'deactivate', 'delete', 'export']
        if v not in allowed_operations:
            raise ValueError(f"Operation must be one of {allowed_operations}")
        return v
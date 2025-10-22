from __future__ import annotations  # 🔹 essentiel pour forward refs
from typing import Optional, List, Any, Dict
from uuid import UUID
from decimal import Decimal
from pydantic import BaseModel, Field, field_validator
from models.enum import CurrencyEnum
from schemas.category_schemas import CategorySimpleOut

# ============================
# 🔹 Schémas de base
# ============================

class ProductBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=150, example="Pizza Margherita")
    description: Optional[str] = Field(None, example="Une délicieuse pizza traditionnelle")
    price: Decimal = Field(..., gt=0, max_digits=10, decimal_places=2, example=12.50)
    compare_at_price: Optional[Decimal] = Field(  # Nouveau
        None, gt=0, max_digits=10, decimal_places=2, example=15.00
    )
    currency: CurrencyEnum = Field(default=CurrencyEnum.XAF)
    is_available: bool = Field(default=True)
    stock_quantity: int = Field(default=0, ge=0)
    low_stock_threshold: int = Field(default=5, ge=0)  # Nouveau
    preparation_time: Optional[int] = Field(None, ge=0, description="Temps en minutes")  # Rétabli
    category_id: Optional[UUID] = Field(None, description="ID de la catégorie")
    sku: Optional[str] = Field(None, max_length=100, example="PROD-001")  # Nouveau
    tags: List[str] = Field(default_factory=list)  # Nouveau
    attributes: Dict[str, Any] = Field(default_factory=dict)  # Type amélioré
    image_urls: List[str] = Field(default_factory=list)  # Nouveau - remplace image_url
    
    model_config = {"from_attributes": True}

    @field_validator('compare_at_price')
    def validate_compare_price(cls, v, values):
        if v is not None and 'price' in values and v <= values['price']:
            raise ValueError('compare_at_price doit être supérieur au prix normal')
        return v

class ProductCreate(ProductBase):
    pass

class ProductUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=150)
    description: Optional[str] = None
    price: Optional[Decimal] = Field(None, gt=0, max_digits=10, decimal_places=2)
    compare_at_price: Optional[Decimal] = Field(None, gt=0, max_digits=10, decimal_places=2)
    currency: Optional[CurrencyEnum] = None
    is_available: Optional[bool] = None
    stock_quantity: Optional[int] = Field(None, ge=0)
    low_stock_threshold: Optional[int] = Field(None, ge=0)
    preparation_time: Optional[int] = Field(None, ge=0)
    category_id: Optional[UUID] = None
    sku: Optional[str] = Field(None, max_length=100)
    tags: Optional[List[str]] = None
    attributes: Optional[Dict[str, Any]] = None
    image_urls: Optional[List[str]] = None
    
    model_config = {"from_attributes": True}

# ============================
# 🔹 Schémas de sortie
# ============================

class ProductSimpleOut(BaseModel):
    id: UUID
    name: str
    price: Decimal
    compare_at_price: Optional[Decimal]
    currency: CurrencyEnum
    is_available: bool
    stock_quantity: int
    image_urls: List[str]
    sku: Optional[str]
    has_discount: bool = Field(False, description="Si le produit est en promo")  # Nouveau
    is_low_stock: bool = Field(False, description="Alerte stock faible")  # Nouveau
    
    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_custom(cls, obj) -> Dict[str, Any]:
        """Version simplifiée pour les listes"""
        data = {
            "id": obj.id,
            "name": obj.name,
            "price": obj.price,
            "compare_at_price": obj.compare_at_price,
            "currency": obj.currency,
            "is_available": obj.is_available,
            "stock_quantity": obj.stock_quantity,
            "image_urls": obj.image_urls or [],
            "sku": obj.sku,
            "has_discount": obj.compare_at_price is not None and obj.compare_at_price > obj.price,
            "is_low_stock": obj.stock_quantity <= (obj.low_stock_threshold or 5)
        }
        return data

class ProductOut(ProductBase):
    id: UUID
    created_at: str  # ou datetime
    updated_at: str  # ou datetime
    created_by: UUID
    is_active: bool
    category: Optional["CategorySimpleOut"] = None  # Relation complète
    
    # Propriétés calculées
    has_discount: bool = Field(False)
    is_low_stock: bool = Field(False)
    discount_percentage: Optional[int] = Field(None, description="Pourcentage de réduction")  # Nouveau
    
    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_custom(cls, obj) -> Dict[str, Any]:
        """Version enrichie avec propriétés calculées"""
        p = cls.model_validate(obj)
        data = p.model_dump()
        
        # Propriétés calculées
        data["has_discount"] = obj.compare_at_price is not None and obj.compare_at_price > obj.price
        data["is_low_stock"] = obj.stock_quantity <= (obj.low_stock_threshold or 5)
        data["discount_percentage"] = None
        
        if data["has_discount"]:
            discount = ((obj.compare_at_price - obj.price) / obj.compare_at_price) * 100
            data["discount_percentage"] = int(discount)
        
        data["summary"] = f"{data['name']} - {data['price']} {data['currency']}"
        return data

# ============================
# 🔹 Schémas de réponse
# ============================

class ProductSummaryOut(BaseModel):  # Nouveau - pour recherches/listing
    id: UUID
    name: str
    price: Decimal
    currency: CurrencyEnum
    image_urls: List[str]
    is_available: bool
    has_discount: bool
    is_low_stock: bool
    category_name: Optional[str] = None
    
    model_config = {"from_attributes": True}

class PaginatedProductsResponse(BaseModel):
    success: bool = True
    message: str
    total: int
    page: int
    page_size: int
    total_pages: int  # Nouveau
    data: List[Dict[str, Any]]
    filters: Optional[Dict[str, Any]] = None  # Nouveau - filtres appliqués
    
    model_config = {"from_attributes": True}

class ProductStockAlertOut(BaseModel):  # Nouveau - pour alertes stock
    product_id: UUID
    product_name: str
    sku: Optional[str]
    current_stock: int
    low_stock_threshold: int
    needs_restock: bool
    
    model_config = {"from_attributes": True}

# ============================
# 🔹 Résolution des références circulaires
# ============================


ProductOut.model_rebuild()

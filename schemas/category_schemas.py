from __future__ import annotations  # 🔹 essentiel pour forward refs
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, Field



# ============================
# 🔹 Schémas de base
# ============================

class CategoryBase(BaseModel):
    name: str = Field(..., example="Fast Food")
    description: Optional[str] = Field(None, example="Produits de restauration rapide")
    parent_id: Optional[UUID] = Field(None, description="ID de la catégorie parente")  # Nouveau
    
    model_config = {
        "from_attributes": True,
        "populate_by_name": True
    }

class CategoryCreate(CategoryBase):
    merchant_id: Optional[UUID] = None  # Null si catégorie globale

class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    parent_id: Optional[UUID] = None  # Nouveau
    
    model_config = {
        "from_attributes": True,
        "populate_by_name": True
    }


# ============================
# 🔹 Schémas de sortie étendus
# ============================

class CategorySimpleOut(CategoryBase):
    id: UUID
    merchant_id: Optional[UUID]
    is_active: bool
    
    
    model_config = {
        "from_attributes": True,
        "populate_by_name": True
    }


class CategoryOut(CategorySimpleOut):
    children: List["CategorySimpleOut"] = Field(default_factory=list)  # Nouveau - catégories enfants
    parent: Optional["CategorySimpleOut"] = None  # Nouveau - catégorie parente
    
    model_config = {
        "from_attributes": True,
        "populate_by_name": True
    }


# ============================
# 🔹 Schémas de réponse
# ============================

class CategoryTreeOut(BaseModel):  # Nouveau - pour l'arborescence complète
    category: CategorySimpleOut
    children: List["CategoryTreeOut"]
    
    model_config = {
        "from_attributes": True,
        "populate_by_name": True
    }


# ============================
# 🔹 Schéma de réponse générique
# ============================

class ResponseSchema(BaseModel):
    success: Optional[bool]
    message: str
    data: Optional[dict] = None  # Si demandé par le client


# 🔹 Mise à jour des références circulaires
CategoryOut.model_rebuild()
CategoryTreeOut.model_rebuild()
from typing import Generic, TypeVar, List,Optional, List
from pydantic import BaseModel, Field, HttpUrl,EmailStr,field_validator,ConfigDict
from models.user_model import BusinessType
from schemas.user_schema import UserCreateSchema, UserOutSchema

T = TypeVar("T")

# ================================================================
# 🧩 1️⃣ - SCHEMA D’ABONNEMENT (lié à SubscriptionPlan)
# ================================================================

class SubscriptionPlanOutSchema(BaseModel):
    """
    Schéma de sortie pour les plans d’abonnement disponibles.
    Permet d’afficher les informations essentielles du plan sélectionné par le marchand.
    """
    code: str = Field(..., description="Code interne du plan d’abonnement (ex: free, basic, pro, premium)")
    name: str = Field(..., description="Nom lisible du plan (affichage utilisateur)")
    description: Optional[str] = Field(None, description="Description du plan et de ses avantages")
    commission_rate: float = Field(..., description="Taux de commission appliqué aux ventes (ex: 0.05 pour 5%)")
    monthly_fee: float = Field(..., description="Frais mensuels fixes associés au plan")
    is_active: bool = Field(..., description="Indique si le plan est actuellement disponible")

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra = {
            "example": {
                "code": "pro",
                "name": "Professionnel",
                "description": "Plan destiné aux marchands réguliers avec un faible taux de commission.",
                "commission_rate": 0.02,
                "monthly_fee": 15000.0,
                "is_active": True
            }
        }
    )

# ================================================================
# 🧱 2️⃣ - DÉTAILS DU MARCHAND
# ================================================================

class MarchantDetailsCreateSchema(BaseModel):
    """Sous-schéma pour les informations spécifiques du marchand."""

    business_name: str = Field(..., description="Nom commercial du marchand", max_length=100)
    business_type: BusinessType = Field(..., description="Type d’activité du marchand")
    description: Optional[str] = Field(None, description="Brève description du commerce", max_length=255)
    banner_url: Optional[HttpUrl] = Field(None, description="Photo ou bannière représentant le local ou le magasin")
    logo_url: Optional[HttpUrl] = Field(None, description="Logo du marchand")
    siret: str = Field(..., min_length=4, max_length=50, description="Numéro unique d'enregistrement du marchand (ex: RCCM ou SIRET)")
    subscription_code: Optional[str] = Field(
        None, description="Code du plan d’abonnement choisi (ex: 'basic', 'pro', etc.)"
    )

    @field_validator("business_name")
    def normalize_name(cls, v):
        return v.strip().title()

    @field_validator("siret")
    def validate_siret(cls, v):
        v = v.strip()
        if len(v) < 4:
            raise ValueError("Le SIRET doit contenir au moins 4 caractères.")
        return v
    
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra = {
            "example": {
                "business_name": "Alice Moto Livraison",
                "business_type": "BOUTIQUE",
                "description": "Vente et livraison de motos et accessoires.",
                "banner_url": "https://cdn.example.com/banners/moto_shop.jpg",
                "logo_url": "https://cdn.example.com/logos/moto_shop.png",
                "siret": "SIRET123456789",
                "subscription_code": "pro"
            }
        }
    )

# ================================================================
# 🧱 2️⃣ - LOCALISATION DU MARCHAND
# ================================================================

class UserLocationCreateSchema(BaseModel):
    """Localisation principale du marchand"""
    address: str
    city: str
    postal_code: str
    country: str
    latitude: float
    longitude: float

    # Champs texte : non vides et strip
    @field_validator("address", "city", "country")
    def not_empty(cls, v, field):
        v = v.strip()
        if not v:
            raise ValueError(f"Le champ '{field.name}' ne peut pas être vide")
        return v

    # Postal code : optionnel mais pas vide si fourni
    @field_validator("postal_code")
    def postal_code_valid(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("Le code postal ne peut pas être vide")
        return v

    # Latitude et longitude : bornes réalistes
    @field_validator("latitude")
    def latitude_valid(cls, v):
        if not -90 <= v <= 90:
            raise ValueError("La latitude doit être comprise entre -90 et 90")
        return v

    @field_validator("longitude")
    def longitude_valid(cls, v):
        if not -180 <= v <= 180:
            raise ValueError("La longitude doit être comprise entre -180 et 180")
        return v


# ================================================================
# 🧠 3️⃣ - CRÉATION DU MARCHAND (avec compte utilisateur)
# ================================================================

class MarchantCreateSchema(BaseModel):
    """Schéma complet pour la création d'un marchand et de son compte utilisateur associé."""

    user_data: UserCreateSchema = Field(..., description="Données du compte utilisateur du marchand")
    details: MarchantDetailsCreateSchema = Field(..., description="Informations spécifiques du commerce")
    location: UserLocationCreateSchema = Field(..., description="Localisation principale du marchand")

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra = {
            "example": {
                "user_data": {
                    "email": "marchant@example.com",
                    "phone": "+237600000000",
                    "password": "SuperPass123",
                    "first_name": "Jean",
                    "last_name": "Moto",
                    "user_type": "merchant"
                },
                "details": {
                    "business_name": "Alice Moto Livraison",
                    "business_type": "boutique",
                    "description": "Vente de motos et accessoires avec service de livraison rapide.",
                    "banner_url": "https://cdn.example.com/banners/moto_shop.jpg",
                    "logo_url": "https://cdn.example.com/logos/moto_shop.png",
                    "siret": "SIRET123456789",
                    "subscription_code": "basic"
                },
                "location":{
                    "address": "123 Rue de la Moto",
                    "city": "Douala",
                    "postal_code": "12345",
                    "country": "Cameroun",
                    "latitude": 4.0511,
                    "longitude": 9.7679
                }
            }
        }
    )

# ================================================================
# 🧾 4️⃣ - MISE À JOUR DES INFOS MARCHAND
# ================================================================

class MarchantUpdateSchema(BaseModel):
    """Schéma pour la mise à jour (partielle) des données d’un marchand."""

    business_name: Optional[str] = Field(None, description="Nom du business du marchand.", max_length=100)
    business_type: Optional[BusinessType] = Field(None, description="Type d’activité du marchand")
    description: Optional[str] = Field(None, description="Description courte du commerce", max_length=255)
    banner_url: Optional[HttpUrl] = Field(None, description="URL de la bannière du marchand")
    logo_url: Optional[HttpUrl] = Field(None, description="URL du logo du marchand")

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra = {
            "example": {
                "business_name": "Alice Moto Livraison",
                "description": "Mise à jour du profil avec une nouvelle bannière",
                "banner_url": "https://cdn.example.com/new_banner.jpg"
            }
        }
    )


#=================================================================
# MISE A JOUR DE L'ABONNEMENT DU MARCHAND
#=================================================================

class MarchantSubscriptionUpdateSchema(BaseModel):
    """Schéma pour la mise à jour du plan d'abonnement d'un marchand."""

    subscription_code: str = Field(..., description="Code du plan d'abonnement à appliquer")

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra = {
            "example": {
                "subscription_code": "pro"
            }
        }
    )


# ================================================================
# 📤 5️⃣ - SORTIES DÉTAILLÉES
# ================================================================

class MarchantDetailsOutputSchema(BaseModel):
    """
    Schéma de sortie complet d’un marchand.
    Utilisé pour le tableau de bord (vue privée).
    """

    user_data: UserOutSchema
    business_name: str
    business_type: BusinessType
    description: Optional[str]
    banner_url: Optional[HttpUrl]
    logo_url: Optional[HttpUrl]
    siret: str
    subscription_plan: Optional[SubscriptionPlanOutSchema] = None

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra = {
            "example": {
                "user_data": {
                    "id": "usr_1234",
                    "email": "marchant@example.com",
                    "first_name": "Jean",
                    "last_name": "Moto",
                    "phone": "+237600000000",
                    "user_type": "Marchant"
                },
                "business_name": "Alice Moto Livraison",
                "business_type": "BOUTIQUE",
                "description": "Vente et livraison de motos.",
                "banner_url": "https://cdn.example.com/banners/moto_shop.jpg",
                "logo_url": "https://cdn.example.com/logos/moto_shop.png",
                "siret": "SIRET123456789",
                "subscription_plan": {
                    "code": "pro",
                    "name": "Professionnel",
                    "commission_rate": 0.02,
                    "monthly_fee": 15000.0,
                    "is_active": True
                }
            }
        }
    )


# ================================================================
# 🌍 6️⃣ - SORTIE PUBLIQUE (vitrine)
# ================================================================

class MarchantDetailsOutputPublicSchema(BaseModel):
    """
    Schéma de sortie public pour afficher un marchand sur la marketplace.
    Contient uniquement les données non sensibles.
    """

    email: EmailStr
    phone: str
    first_name: str
    last_name: str
    rating: float = Field(..., ge=0, le=5, description="Note moyenne du marchand (0 à 5)")
    business_name: str
    business_type: BusinessType
    description: Optional[str]
    logo_url: Optional[HttpUrl]

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra = {
            "example": {
                "email": "marchant@example.com",
                "first_name": "Jean",
                "last_name": "Moto",
                "phone": "+237600000000",
                "rating": 4.7,
                "business_name": "Alice Moto Livraison",
                "business_type": "BOUTIQUE",
                "description": "Livraison rapide et service de qualité.",
                "logo_url": "https://cdn.example.com/logos/moto_shop.png"
            }
        }
    )


# ================================================================
# ✅ 7️⃣ - RÉPONSE GÉNÉRIQUE DE SUCCÈS
# ================================================================

class MarchantSuccesRequestSchema(BaseModel):
    """Schéma standard pour les réponses de succès."""

    detail: str = Field(..., description="Message de confirmation")

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra = {"example": {"detail": "Opération effectuée avec succès"}}
    )


#==============================================================
# Pagination générique pour les marchands
#==============================================================

class PaginatedResponseSchema(BaseModel, Generic[T]):
    items: List[T] = []
    limit: int
    offset: int
    page: int  # numéro de la page actuelle
    total: int  # nombre total d'éléments
    total_pages: int  # nombre total de pages
    has_next: bool
    has_previous: bool

# ================================================================
# 💵 8️⃣ - HISTORIQUE DES VENTES (placeholder pour ton futur service)
# ================================================================

class MarchantSaleHistorySchema(BaseModel):
    """Historique des ventes d’un marchand — à compléter avec le service de ventes."""
    sale_id: str
    total_amount: float
    commission_amount: float
    net_amount: float
    sale_date: str  # ISO datetime string

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra = {
            "example": {
                "sale_id": "SALE12345",
                "total_amount": 10000.0,
                "commission_amount": 200.0,
                "net_amount": 9800.0,
                "sale_date": "2025-10-20T09:00:00Z"
            }
        }
    )

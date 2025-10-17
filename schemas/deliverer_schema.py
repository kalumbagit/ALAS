from pydantic import BaseModel, Field, validator, HttpUrl
from typing import Optional, List
from datetime import datetime

from models.user_model import IdentityType, VehicleType
from schemas.user_schema import UserCreateSchema,UserOutSchema,UserUpdateSchema


class DelivererDetailsCreateSchema(BaseModel):
    """Sous-schéma pour les informations spécifiques du livreur"""
    vehicle_type: VehicleType = Field(..., description="Type de véhicule du livreur")
    identity_type: IdentityType = Field(..., description="Type de pièce d'identité")
    identity_code: str = Field(..., description="Numéro de la pièce d'identité")
    sponsor_code: Optional[str] = Field(None, description="Code du parrain (si le livreur est parrainé)")
    identity_document_url: Optional[HttpUrl] = Field(None, description="URL du document d'identité scanné")
    selfie_photo_url: Optional[HttpUrl] = Field(None, description="URL de la photo d'identité")

class DelivererCreateSchema(BaseModel):
    """Schéma complet pour la création d'un livreur (avec compte utilisateur)"""
    user_data: UserCreateSchema = Field(..., description="Données du compte utilisateur associé")
    details: DelivererDetailsCreateSchema = Field(..., description="Détails spécifiques du livreur")

    class Config:
        schema_extra = {
            "example": {
                "user_data": {
                    "email": "livreur@example.com",
                    "phone": "+237600000000",
                    "password": "SuperPass123",
                    "first_name": "Jean",
                    "last_name": "Moto",
                    "user_type": "DELIVERER"
                },
                "details": {
                    "vehicle_type": "MOTORCYCLE",
                    "identity_type": "ID_CARD",
                    "sponsor_code": "PARRAIN123",
                    "identity_code":"XXXXXXXXXX",
                    "identity_document_url":"http://*******************",
                    "selfie_photo_url":"http://*******************"
                }
            }
        }
    
class DelivererUpdateSchema(BaseModel):
    """Schéma pour la mise à jour des données d'un livreur (modifiables par lui-même)."""

    vehicle_type: Optional[VehicleType] = Field(None, description="Type de véhicule du livreur")
    identity_code: Optional[str] = Field(None, description="Numéro de la pièce d'identité")
    general: Optional[UserUpdateSchema] = Field(None, description="Informations utilisateur associées")

class DelivererDetailsOutputSchema(BaseModel):
    """
    Schéma de sortie pour les informations détaillées d’un livreur,
    utilisé notamment pour afficher son tableau de bord.
    """
    user_data: UserOutSchema = Field(..., description="Données du compte utilisateur associé")
    vehicle_type: VehicleType = Field(..., description="Type de véhicule utilisé par le livreur")

    total_earnings: float = Field(..., description="Total des gains du livreur (livraisons + parrainages)")
    referral_earnings: float = Field(..., description="Total des gains liés aux parrainages")
    completed_deliveries: int = Field(..., description="Nombre total de livraisons terminées")
    total_referals: int = Field(..., description="Nombre total de parainages")

    class Config:
        schema_extra = {
            "example": {
                "user_data": {
                    "id": "usr_1234",
                    "email": "livreur@example.com",
                    "first_name": "Jean",
                    "last_name": "Moto",
                    "phone": "+237600000000",
                    "user_type": "DELIVERER"
                },
                "vehicle_type": "MOTORCYCLE",
                "total_earnings": 54000.0,
                "referral_earnings": 8000.0,
                "completed_deliveries": 128,
                "total_referals":80
            }
        }

class DelivererStatusUpdateSchema(BaseModel):
    """
    Schéma pour la mise à jour du statut livreur pour dire s'il paut etre inclue dans une recherche ou pas.
    """
    is_online: bool

    class Config:
        json_schema_extra = {
            "example": {
                "is_online": True
            }
        }

class DelivererSuspensionActiveSchema(BaseModel):
    """
    Schéma pour indiquer si un livreur est suspendu ou non.
    """
    is_suspended: bool
    suspension_raison:str = Field(..., description="Raison de la suspension")
    suspension_end:Optional[datetime] = Field(None, description="Date de fin de la suspension")

    class Config:
        json_schema_extra = {
            "example": {
                "is_suspended": False
            }
        }

class DelivererSuspensionDesactivateSchema(BaseModel):
    """
    Schéma pour la désactivation de la suspension d'un livreur.
    """
    detail: str = Field(..., description="Message de confirmation de la désactivation de la suspension")

    class Config:
        schema_extra = {
            "example": {
                "detail": "Livreur réactivé avec succès"
            }
        }

class DelivererSuccesRequestSchema(BaseModel):
    """
    Schéma pour les requetes terminées avec succes.
    """
    detail: str = Field(..., description="operation effectuée avec succès")

    class Config:
        schema_extra = {
            "example": {
                "detail": "operation effectuée avec succès"
            }
        }

class DelivererReferralHistorySchema(BaseModel):
    id: str
    name: str
    verified: bool
    date: datetime


#-----------------------------------------------------
# ces methodes serons deplacer vers un services qui est specialement en charge 
#-----------------------------------------------------

class DelivererEarningsSchema(BaseModel):
    id: str
    deliverer_id: str
    amount: float
    is_advance_payment: bool
    description: str
    status: str
    payment_date: datetime
    delivery_reference: Optional[str]
    updated_at: datetime
    total_earnings: float
    referral_earnings: float

    class Config:
        orm_mode = True

class DelivererEarningsCreateEventSchema(BaseModel):
    deliverer_id: str
    amount: float = Field(..., gt=0, description="Montant du gain, doit être positif")
    description: Optional[str] = Field(None, description="Description du gain")
    is_advance_payment: Optional[bool] = Field(None, description="True si payé à l'avance")
    delivery_reference: Optional[str] = Field(
        None,
        max_length=100,
        description="Référence unique de la livraison associée"
    )

    @validator("delivery_reference")
    def check_delivery_reference(cls, v):
        if v and len(v.strip()) == 0:
            raise ValueError("La référence de livraison ne peut pas être vide")
        return v

    
    class Config:
        schema_extra = {
            "example": {
                "deliverer_id": "uuid-livreur-1234",
                "amount": 150.0,
                "description": "Bonus livraison",
                "is_advance_payment": False,
                "status": "PENDING"
            }
        }

class DelivererEarningsStatusChangeSchema(BaseModel):
    earning_id: str
    delivery_reference:str

from typing import List
import json
from fastapi import APIRouter, Depends, status, Query,File,UploadFile,Form

from services.file_service import upload_identity_document
from schemas.deliverer_schema import (
    DelivererCreateSchema,
    DelivererUpdateSchema,
    DelivererDetailsOutputSchema,
    DelivererStatusUpdateSchema,
    DelivererReferralHistorySchema,
    DelivererSuspensionActiveSchema,
    DelivererSuspensionDesactivateSchema,
    DelivererEarningsSchema,
    DelivererEarningsCreateEventSchema,
    DelivererSuccesRequestSchema

)
from services.deliverer_service import DelivererService
from controllers.user_controller import require_admin,require_access_token,handle_exception,User,UnauthorizedException,UserType 


# ====================================================
# INITIALISATION
# ====================================================
deliverer_service = DelivererService()

router = APIRouter(prefix="/deliverers", tags=["Deliverers - User Access"])
admin_router = APIRouter(prefix="/admin/manage/deliverers", tags=["Deliverers - Admin Access"])


# ====================================================
# 🔹 ROUTES UTILISATEURS (ACCES LIVREUR)
# ====================================================

@router.post("/", response_model=DelivererSuccesRequestSchema, status_code=status.HTTP_201_CREATED)
async def create_deliverer(
    deliverer: str = Form(..., description="Données JSON du livreur"),
    identity_document: UploadFile = File(..., description="Fichier de la pièce d'identité"),
    selfie_photo: UploadFile = File(..., description="Photo de profil / selfie")
):
    """
    Crée un compte livreur avec ses documents associés.
    """
    try:
        # 🔍 Parse la chaîne JSON envoyée via form-data
        deliverer_data = json.loads(deliverer)

        # ✅ Validation via ton schéma Pydantic
        deliverer_obj = DelivererCreateSchema(**deliverer_data)

        # 🗂️ Upload des fichiers
        identity_url = await upload_identity_document(identity_document)
        selfie_url = await upload_identity_document(selfie_photo)

        # 🔗 Ajout des URLs dans le modèle
        deliverer_obj.details.identity_document_url = identity_url
        deliverer_obj.details.selfie_photo_url = selfie_url

        return await deliverer_service.create_deliverer(deliverer_obj)
    except Exception as e:
        handle_exception(e)

@router.get("/{user_id}", response_model=DelivererDetailsOutputSchema)
async def get_deliverer(user_id: str, user: None = Depends(require_access_token)):
    """Récupère les infos d’un livreur connecté ou spécifique."""
    try:
        # Vérification de l'identité
        if (str(user.id) != str(user_id))and (user.user_type != UserType.ADMIN):
            raise UnauthorizedException(detail="Accès refusé : utilisateur non autorisé")
        
        return await deliverer_service.get_deliverer(user_id)
    except Exception as e:
        handle_exception(e)

@router.patch("/{user_id}", response_model=DelivererSuccesRequestSchema)
async def update_deliverer(user_id: str, data: DelivererUpdateSchema, user: None = Depends(require_access_token)):
    """Mise à jour partielle du profil livreur."""
    try:
        # Vérification de l'identité
        if (str(user.id) != str(user_id))and (user.user_type != UserType.ADMIN):
            raise UnauthorizedException(detail="Accès refusé : utilisateur non autorisé")
        return await deliverer_service.update_deliverer(user_id, data.dict(exclude_unset=True))
    except Exception as e:
        handle_exception(e)

@router.patch("/{user_id}/status/online", response_model=DelivererStatusUpdateSchema)
async def set_online_status(user_id: str, online: bool, user: None = Depends(require_access_token)):
    """Met à jour le statut en ligne/hors ligne du livreur."""
    try:
        # Vérification de l'identité
        if (str(user.id) != str(user_id))and (user.user_type != UserType.ADMIN):
            raise UnauthorizedException(detail="Accès refusé : utilisateur non autorisé")
        
        return await deliverer_service.set_online_status(user_id, online)
    except Exception as e:
        handle_exception(e)

# ====================================================
# 🔸 ROUTES ADMIN (GESTION ET SUPERVISION)
# ====================================================

@admin_router.get("/", response_model=List[DelivererDetailsOutputSchema])
async def list_deliverers(limit: int = 50, offset: int = 0, admin: None = Depends(require_admin)):
    """Liste paginée de tous les livreurs (admin uniquement)."""
    try:
        return await deliverer_service.list_deliverers(limit=limit, offset=offset)
    except Exception as e:
        handle_exception(e)

@admin_router.delete("/{user_id}",response_model=DelivererSuccesRequestSchema, status_code=status.HTTP_200_OK)
async def delete_deliverer(user_id: str, admin: None = Depends(require_admin)):
    """Supprime un livreur du système (action irréversible)."""
    try:
        await deliverer_service.delete_deliverer(user_id)
        return DelivererSuccesRequestSchema(detail="Livreur supprimé avec succès")
    except Exception as e:
        handle_exception(e)

@admin_router.patch("/{user_id}/suspend", response_model=DelivererSuspensionActiveSchema)
async def suspend_deliverer(
    user_id: str,
    days: int = Query(..., gt=0, description="Durée de suspension en jours"),
    reason: str = Query(..., description="Motif de la suspension"),
    admin: None = Depends(require_admin)
):
    """Suspend temporairement un livreur pour un motif donné."""
    try:
        return await deliverer_service.suspend_deliverer(user_id, days, reason)
    except Exception as e:
        handle_exception(e)

@admin_router.patch("/{user_id}/reactivate", response_model=DelivererSuspensionDesactivateSchema)
async def reactivate_deliverer(user_id: str, admin: None = Depends(require_admin)):
    """Réactive un livreur précédemment suspendu."""
    try:
        return await deliverer_service.reactivate_deliverer(user_id)
    except Exception as e:
        handle_exception(e)

@admin_router.patch("/{deliverer_id}/earnings", response_model=DelivererEarningsSchema)
async def add_delivery_earning(
    deliverer_schema: DelivererEarningsCreateEventSchema,
    admin: None = Depends(require_admin)
):
    """Ajoute des gains à un livreur (bonus, parrainage, etc.)."""
    try:
        return await deliverer_service.add_delivery_earning(deliverer_schema)
    except Exception as e:
        handle_exception(e)

@admin_router.get("/{user_id}/deliveries", response_model=list[DelivererReferralHistorySchema])
async def get_referral_history(user_id: str, admin: None = Depends(require_admin)):
    """Incrémente le nombre de livraisons complétées d’un livreur."""
    try:
        return await deliverer_service.get_referral_history(user_id)
    except Exception as e:
        handle_exception(e)

@admin_router.post("/{user_id}/verify_identity", response_model=dict)
async def verify_identity(user_id: str,admin: User = Depends(require_admin)):
    """Incrémente le nombre de livraisons complétées d’un livreur."""
    try:
        # Ici admin est déjà une instance de User (ou un schéma Pydantic selon ton système d’auth)
        admin_id = admin.id
        return await deliverer_service.verify_identity(user_id,admin_id)
    except Exception as e:
        handle_exception(e)




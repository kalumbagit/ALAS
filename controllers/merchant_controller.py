# ====================================================
# 📦 IMPORTS
# ====================================================

# --- Standard ---
import json
from typing import List, Optional

# --- FastAPI ---
from fastapi import (
    APIRouter,
    Depends,
    Query,
    Path,
    Form,
    UploadFile,
    File,
    status
)

# --- Core ---
from core.config import settings
from core.exceptions import APIException, UnauthorizedException
from core.logging import logger

# --- Services ---
from services.merchant_service import MerchantService
from services.file_service import upload_identity_document

# --- Schemas ---
from schemas.merchant_schema import (
    MarchantCreateSchema,
    MarchantUpdateSchema,
    MarchantSubscriptionUpdateSchema,
    MarchantDetailsOutputSchema,
    MarchantDetailsOutputPublicSchema,
    PaginatedResponseSchema,
    MarchantSuccesRequestSchema,
    SubscriptionPlanOutSchema
)

# --- Auth / Utils ---
from controllers.user_controller import (
    require_admin,
    require_access_token,
    handle_exception,
    User,
    UserType
)


# ====================================================
# ⚙️ INITIALISATION
# ====================================================

router = APIRouter(prefix="/merchants", tags=["Merchants - User Access"])
admin_router = APIRouter(prefix="/admin/manage/merchants", tags=["Merchants - Admin Access"])

service = MerchantService()


# ====================================================
# 🌍 PUBLIC ACCESS ROUTES
# ====================================================

@router.get(
    "/public/{merchant_id}",
    response_model=MarchantDetailsOutputPublicSchema,
    status_code=status.HTTP_200_OK,
    summary="Obtenir les informations publiques d’un marchand",
    description="Retourne les informations visibles publiquement d’un marchand (exposées sur le front public)."
)
async def get_public_merchant(merchant_id: str = Path(..., description="Identifiant du marchand")):
    try:
        return await service.get_public_merchant(merchant_id)
    except Exception as e:
        handle_exception(e)


# ====================================================
# 🔐 AUTHENTICATED USER ACCESS
# ====================================================

@router.post(
    "/",
    response_model=MarchantSuccesRequestSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Créer un compte marchand",
    description="Permet à un utilisateur de créer son compte marchand avec les documents nécessaires (bannière, logo)."
)
async def create_merchant(
    merchant: str = Form(..., description="Données JSON du marchand"),
    banner: UploadFile = File(..., description="Image de la bannière du commerce"),
    logo: Optional[UploadFile] = File(None, description="Logo de l’entreprise")
):
    try:
        merchant_data = json.loads(merchant)
        merchant_obj = MarchantCreateSchema(**merchant_data)

        # Upload fichiers
        banner_url = await upload_identity_document(banner, settings.MINIO_BUCKET_MERCHANT_DOCS)
        logo_url = await upload_identity_document(logo, settings.MINIO_BUCKET_MERCHANT_DOCS) if logo else None

        merchant_obj.details.banner_url = banner_url
        merchant_obj.details.logo_url = logo_url

        return await service.create_merchant(merchant_obj)
    except APIException as e:
        handle_exception(e)


@router.get(
    "/subscription-plans",
    response_model=List[SubscriptionPlanOutSchema],
    status_code=status.HTTP_200_OK,
    summary="Lister les plans d’abonnement disponibles",
    description="Rafraîchit la table des plans depuis l’enum si nécessaire, puis retourne la liste de tous les plans actifs."
)
async def get_subscription_plans():
    try:
        return await service.seed_subscription_plans()
    except APIException as e:
        handle_exception(e)


@router.get(
    "/{user_id}",
    response_model=MarchantDetailsOutputSchema,
    status_code=status.HTTP_200_OK,
    summary="Obtenir les informations privées d’un marchand",
    description="Récupère les informations complètes d’un marchand connecté. Nécessite un token d’accès valide."
)
async def get_merchant(
    user_id: str = Path(..., description="Identifiant utilisateur du marchand"),
    user: User = Depends(require_access_token)
):
    try:
        # Vérification de l’identité
        if str(user.id) != str(user_id) and user.user_type != UserType.ADMIN:
            raise UnauthorizedException(detail="Accès refusé : utilisateur non autorisé")

        return await service.get_merchant(user_id)
    except Exception as e:
        handle_exception(e)


@router.patch(
    "/{user_id}",
    response_model=MarchantSuccesRequestSchema,
    status_code=status.HTTP_200_OK,
    summary="Mettre à jour les informations d’un marchand",
    description="Permet à un marchand connecté de modifier les détails de son commerce (nom, description, visuels…)."
)
async def update_merchant(
    user_id: str,
    payload: MarchantUpdateSchema,
    user: User = Depends(require_access_token)
):
    try:
        if str(user.id) != str(user_id) and user.user_type != UserType.ADMIN:
            raise UnauthorizedException(detail="Accès refusé : utilisateur non autorisé")

        return await service.update_merchant(user_id, payload)
    except Exception as e:
        handle_exception(e)


@router.patch(
    "/{user_id}/subscription",
    response_model=MarchantSuccesRequestSchema,
    status_code=status.HTTP_200_OK,
    summary="Modifier le plan d’abonnement d’un marchand",
    description="Permet à un marchand de changer de plan d’abonnement. Applique le plan 'FREE' par défaut si aucun plan actif n’est défini."
)
async def update_subscription(
    user_id: str,
    payload: MarchantSubscriptionUpdateSchema,
    user: User = Depends(require_access_token)
):
    try:
        if str(user.id) != str(user_id) and user.user_type != UserType.ADMIN:
            raise UnauthorizedException(detail="Accès refusé : utilisateur non autorisé")

        return await service.update_merchant_subscription(user_id, payload)
    except Exception as e:
        handle_exception(e)


# ====================================================
# 🛡️ ADMIN ACCESS ROUTES
# ====================================================

@admin_router.get(
    "/",
    response_model=PaginatedResponseSchema[MarchantDetailsOutputSchema],
    status_code=status.HTTP_200_OK,
    summary="Lister les marchands (admin)",
    description="Retourne une liste paginée des marchands enregistrés. Réservé aux administrateurs."
)
async def list_merchants(
    limit: int = Query(50, ge=1, le=100, description="Nombre d’éléments par page"),
    offset: int = Query(0, ge=0, description="Décalage pour la pagination"),
    admin: User = Depends(require_admin)
):
    try:
        return await service.list_merchants(limitInt=limit, offsetInt=offset)
    except Exception as e:
        handle_exception(e)


@admin_router.delete(
    "/{user_id}",
    response_model=MarchantSuccesRequestSchema,
    status_code=status.HTTP_200_OK,
    summary="Supprimer un marchand (admin)",
    description="Supprime un marchand de la base de données ainsi que ses informations associées. Réservé aux administrateurs."
)
async def delete_merchant(
    user_id: str,
    admin: User = Depends(require_admin)
):
    try:
        return await service.delete_merchant(user_id)
    except Exception as e:
        handle_exception(e)



from datetime import datetime, timezone
from typing import Optional, List

from tortoise.transactions import in_transaction
from tortoise.exceptions import DoesNotExist, IntegrityError

from models.user_model import User, Merchant,SubscriptionPlan,UserLocation  # ton modèle Merchant (Tortoise)

from core.exceptions import (
    NotFoundException,
    ConflictException,
    InternalServerException,
    APIException,
)
from core.logging import logger
from services.user_service import UserService

# Schémas (utilise bien les schémas que tu as fournis précédemment)
from schemas.merchant_schema import (
    MarchantCreateSchema,
    MarchantDetailsOutputSchema,
    MarchantDetailsOutputPublicSchema,
    MarchantSuccesRequestSchema,
    SubscriptionPlanOutSchema,
    MarchantSaleHistorySchema,
    PaginatedResponseSchema,
    MarchantSuccesRequestSchema,
    MarchantUpdateSchema,
    MarchantSubscriptionUpdateSchema
)
from schemas.user_schema import UserOutSchema


class MerchantService:
    """
    Service complet pour la gestion des marchands.
    Responsable de :
    - création / lecture / mise à jour / suppression des marchands
    - gestion du choix du plan d'abonnement (liaison Merchant <-> SubscriptionPlan)
    - listing public/privé des marchands
    """

    def __init__(self):
        self.user_service = UserService()
    # ------------------------------
    # Seed des plans depuis la table/enum (optionnel)
    # ------------------------------
    async def seed_subscription_plans(self):
        """
        Appelle la méthode de seed du modèle SubscriptionPlan pour synchroniser
        la table des plans à partir de l'enum (si implémentée).
        """
        try:
            # 1️⃣ Seed depuis l'enum si disponible
            if hasattr(SubscriptionPlan, "seed_from_enum"):
                await SubscriptionPlan.seed_from_enum()
                logger.info("Subscription plans seeded from enum.")
            else:
                logger.info("Aucune méthode seed_from_enum sur SubscriptionPlan.")
            
            # 2️⃣ Récupération des plans actifs après seed
            active_plans = await SubscriptionPlan.filter(is_active=True)

            # Conversion en schema de sortie
            return [
                SubscriptionPlanOutSchema(
                    code=plan.code,
                    name=plan.name,
                    description=plan.description,
                    commission_rate=float(plan.commission_rate),
                    monthly_fee=float(plan.monthly_fee),
                    is_active=bool(plan.is_active)
                )
                for plan in active_plans
            ]
        except Exception as e:
            logger.exception(f"Erreur lors du seed des SubscriptionPlan: {e}")
            raise InternalServerException(detail="Impossible de synchroniser les plans d'abonnement.")

    # ------------------------------
    # Création d'un marchand + création du User associé
    # ------------------------------
    async def create_merchant(self, merchant_input: MarchantCreateSchema) -> MarchantSuccesRequestSchema:
        """
        Crée l'utilisateur, le marchand et sa localisation principale.
        Toutes les opérations sont atomiques et rollback si une exception survient.
        """
        user_model = None
        created_objects = []

        try:
            async with in_transaction():
                # 1️⃣ Création du user (via UserService)
                user = await self.user_service.create_user(merchant_input.user_data)
                created_objects.append(('user', user.id))
                user_model = await User.get(id=user.id)

                # 2️⃣ Récupération du plan d’abonnement
                subscription_code = merchant_input.details.subscription_code
                subscription_plan = await SubscriptionPlan.get_or_none(code=subscription_code or "free")
                if not subscription_plan:
                    logger.warning(
                        f"Code d'abonnement inconnu '{subscription_code}', application du plan FREE."
                    )
                    subscription_plan = await SubscriptionPlan.get_or_none(code="free")

                if not subscription_plan:
                    logger.error("Le plan FREE est introuvable en base.")
                    raise InternalServerException(detail="Plan FREE introuvable dans la base de données.")

                # 3️⃣ Création du marchand
                merchant = await Merchant.create(
                    user=user_model,
                    business_name=merchant_input.details.business_name.strip(),
                    business_type=merchant_input.details.business_type,
                    description=merchant_input.details.description,
                    banner_url=str(merchant_input.details.banner_url) if merchant_input.details.banner_url else None,
                    logo_url=str(merchant_input.details.logo_url) if merchant_input.details.logo_url else None,
                    siret=merchant_input.details.siret.strip(),
                    subscription_plan=subscription_plan
                )
                created_objects.append(('merchant', merchant.id))

                # 4️⃣ Création de la localisation principale
                loc_data = merchant_input.location
                location = await UserLocation.create(
                    user=user_model,
                    address=loc_data.address,
                    city=loc_data.city,
                    postal_code=loc_data.postal_code,
                    country=loc_data.country,
                    latitude=loc_data.latitude,
                    longitude=loc_data.longitude,
                    is_primary=True
                )
                created_objects.append(('location', location.id))

                logger.info(f"✅ Marchand créé avec succès : {merchant.id} (user: {user.id})")
                return MarchantSuccesRequestSchema(detail="Marchand créé avec succès")

        except (ConflictException, IntegrityError) as e:
            logger.warning(f"⚠️ Conflit ou erreur d’intégrité lors de la création : {str(e)}")
            await self._cleanup_created_objects(created_objects)
            raise ConflictException(detail=str(e))

        except Exception as e:
            logger.exception(f"💥 Erreur interne inattendue : {e}")
            await self._cleanup_created_objects(created_objects)
            raise InternalServerException(detail="Erreur interne lors de la création du marchand")


    async def _cleanup_created_objects(self, created_objects: list[tuple[str, str]]):
        """
        Supprime tous les objets créés (user, merchant, location) en cas d'erreur.
        La suppression est sûre et ne bloque jamais si un objet n'existe plus.
        """
        for obj_type, obj_id in reversed(created_objects):
            try:
                if obj_type == 'merchant':
                    m = await Merchant.get_or_none(id=obj_id)
                    if m:
                        await m.delete()
                        logger.info(f"🧹 Merchant {obj_id} supprimé lors du rollback.")
                elif obj_type == 'location':
                    loc = await UserLocation.get_or_none(id=obj_id)
                    if loc:
                        await loc.delete()
                        logger.info(f"🧹 Location {obj_id} supprimée lors du rollback.")
                elif obj_type == 'user':
                    u = await User.get_or_none(id=obj_id)
                    if u:
                        await u.delete()
                        logger.info(f"🧹 User {obj_id} supprimé lors du rollback.")
            except Exception as cleanup_error:
                logger.error(f"Échec de suppression de {obj_type} {obj_id} : {cleanup_error}")

    # ------------------------------
    # Récupérer un marchand par user_id (vue privée)
    # ------------------------------
    async def get_merchant(self, user_id: str) -> MarchantDetailsOutputSchema:
        """
        Récupère les détails d’un marchand (vue privée / dashboard).
        Inclut le user_data et le plan d'abonnement lié si présent.
        """
        try:
            merchant = await Merchant.get(user=user_id).prefetch_related("user", "subscription_plan")

            user_data = UserOutSchema.from_orm(merchant.user)

            subscription_plan_data: Optional[SubscriptionPlanOutSchema] = None
            if merchant.subscription_plan:
                sp = merchant.subscription_plan
                subscription_plan_data = SubscriptionPlanOutSchema(
                    code=sp.code,
                    name=sp.name,
                    description=sp.description,
                    commission_rate=float(sp.commission_rate),
                    monthly_fee=float(sp.monthly_fee),
                    is_active=bool(sp.is_active),
                )

            return MarchantDetailsOutputSchema(
                user_data=user_data,
                business_name=merchant.business_name,
                business_type=merchant.business_type,
                description=merchant.description,
                banner_url=merchant.banner_url,
                logo_url=merchant.logo_url,
                siret=merchant.siret,
                subscription_plan=subscription_plan_data,
            )

        except DoesNotExist:
            raise NotFoundException(detail="Marchand introuvable")
        except Exception as e:
            logger.exception(f"Erreur lors de la récupération du marchand {user_id}: {e}")
            raise InternalServerException(detail="Erreur interne lors de la récupération du marchand")

    # ------------------------------
    # Récupérer la fiche publique d'un marchand (vitrine)
    # ------------------------------
    async def get_public_merchant(self, merchant_id: str) -> MarchantDetailsOutputPublicSchema:
        """
        Vue publique du marchand : ne contient pas d'informations sensibles.
        Accepts merchant_id (UUID) or user_id depending de ton implementation – ici on assume merchant.id.
        """
        try:
            merchant = await Merchant.get(id=merchant_id).prefetch_related("user")
            user = merchant.user

            return MarchantDetailsOutputPublicSchema(
                email=user.email,
                phone=user.phone,
                first_name=user.first_name,
                last_name=user.last_name,
                rating=merchant.rating,
                business_name=merchant.business_name,
                business_type=merchant.business_type,
                description=merchant.description,
                logo_url=merchant.logo_url,
            )

        except DoesNotExist:
            raise NotFoundException(detail="Marchand introuvable")
        except Exception as e:
            logger.exception(f"Erreur lors de la récupération publique du marchand {merchant_id}: {e}")
            raise InternalServerException(detail="Erreur interne lors de la récupération publique du marchand")

    # ------------------------------
    # Liste des marchands (privée / admin) avec pagination
    # ------------------------------
    async def list_merchants(self, limitInt: int = 50, offsetInt: int = 0) -> PaginatedResponseSchema[MarchantDetailsOutputSchema]:
        """
        Retourne la liste paginée des marchands (vue privée / admin).
        """
        try:
            limit = max(1, min(limitInt, 100))  # limite max pour éviter surcharges
            offset = max(0, offsetInt)  # indice de départ pour récupérer les éléments dans la base de données
            total_count = await Merchant.all().count()
            total_pages = (total_count + limit - 1) // limit  # arrondi supérieur
            merchants = (
                await Merchant.all()
                .limit(limit)
                .offset(offset)
                .prefetch_related("user", "subscription_plan")
            )

            result: List[MarchantDetailsOutputSchema] = []
            for m in merchants:
                user_data = UserOutSchema.from_orm(m.user)
                sp_data = None
                if m.subscription_plan:
                    sp = m.subscription_plan
                    sp_data = SubscriptionPlanOutSchema(
                        code=sp.code,
                        name=sp.name,
                        description=sp.description,
                        commission_rate=float(sp.commission_rate),
                        monthly_fee=float(sp.monthly_fee),
                        is_active=bool(sp.is_active),
                    )

                result.append(
                    MarchantDetailsOutputSchema(
                        user_data=user_data,
                        business_name=m.business_name,
                        business_type=m.business_type,
                        description=m.description,
                        banner_url=m.banner_url,
                        logo_url=m.logo_url,
                        siret=m.siret,
                        subscription_plan=sp_data,
                    )
                )
            current_page = (offset // limit) + 1
            has_next = current_page < total_pages
            has_previous = current_page > 1

            return PaginatedResponseSchema[MarchantDetailsOutputSchema](
                        items=result,
                        limit=limit,
                        offset=offset,
                        page=current_page,
                        total=total_count,
                        total_pages=total_pages,
                        has_next=has_next,
                        has_previous=has_previous
                    )

        except Exception as e:
            logger.exception(f"Erreur lors de la récupération de la liste des marchands: {e}")
            raise InternalServerException(detail="Impossible de récupérer la liste des marchands pour le moment")

    # ------------------------------
    # Mise à jour partielle du marchand (et choix / changement de plan)
    # ------------------------------
    async def update_merchant(self, user_id: str, data: MarchantUpdateSchema) -> MarchantSuccesRequestSchema:
        """
        Met à jour les informations d'un marchand.
        Si 'subscription_code' est présent, on tente de lier le Merchant au SubscriptionPlan correspondant.
        """
        try:
            merchant = await Merchant.get(user=user_id)

            # Mise à jour des champs du Merchant
            update_data = data.dict(exclude_unset=True)
            for key, value in update_data.items():
                if hasattr(merchant, key):
                    setattr(merchant, key, value)

            await merchant.save()

            # Conversion en schema de sortie
            return MarchantSuccesRequestSchema(detail="Marchand mis à jour avec succès")

        except DoesNotExist:
            raise NotFoundException(detail="Marchand introuvable")
        except IntegrityError as e:
            logger.exception(f"Erreur d'intégrité lors de la mise à jour du marchand {user_id}: {e}")
            raise ConflictException(detail="Erreur lors de la mise à jour du marchand (doublon ou contrainte)")
        except APIException:
            raise
        except Exception as e:
            logger.exception(f"Erreur interne lors de la mise à jour du marchand {user_id}: {e}")
            raise InternalServerException(detail="Erreur interne lors de la mise à jour du marchand")

    async def update_merchant_subscription(
        self, user_id: str, data: "MarchantSubscriptionUpdateSchema"
    ) -> MarchantSuccesRequestSchema:
        """
        Met à jour uniquement le plan d'abonnement d'un marchand.

        Règles :
        - Vérifie que le plan demandé existe.
        - Vérifie que le plan est actif.
        - Change le plan seulement si différent du plan actuel.
        - Si le marchand n'a pas de plan, applique FREE par défaut.
        """
        try:
            merchant = await Merchant.get(user=user_id).prefetch_related("subscription_plan")

            # S'assure qu'un plan par défaut existe si aucun n'est attribué
            if not merchant.subscription_plan:
                default_plan = await SubscriptionPlan.get_or_none(code="FREE")
                if not default_plan:
                    logger.error("Le plan FREE n'existe pas dans la base de données.")
                    raise InternalServerException(detail="Plan FREE introuvable dans la base de données.")
                merchant.subscription_plan = default_plan
                await merchant.save()

            # Récupération du plan demandé
            requested_plan = await SubscriptionPlan.get_or_none(code=data.subscription_code)
            if not requested_plan:
                logger.warning(f"Code d'abonnement inconnu '{data.subscription_code}'. Le plan FREE sera appliqué.")
                requested_plan = await SubscriptionPlan.get_or_none(code="FREE")

            if not requested_plan:
                logger.error("Le plan FREE n'existe pas dans la base de données. Mise à jour impossible.")
                raise InternalServerException(detail="Plan FREE introuvable dans la base de données.")

            # Vérifie si le plan est actif
            if not requested_plan.is_active:
                raise APIException(detail=f"Le plan '{requested_plan.code}' n'est pas actif.")

            # Si le plan demandé est le même que l'actuel, ne rien faire
            if merchant.subscription_plan.id == requested_plan.id:
                logger.info(f"Le marchand {user_id} est déjà sur le plan '{requested_plan.code}'. Aucun changement effectué.")
                return MarchantSuccesRequestSchema(detail="Le plan d'abonnement est déjà à jour.")

            # Mise à jour du plan
            merchant.subscription_plan = requested_plan
            merchant.updated_at = datetime.now(timezone.utc)
            await merchant.save()

            logger.info(f"Plan du marchand {user_id} mis à jour vers '{requested_plan.code}'.")
            return MarchantSuccesRequestSchema(detail=f"Plan d'abonnement mis à jour vers '{requested_plan.name}' avec succès.")

        except DoesNotExist:
            raise NotFoundException(detail="Marchand introuvable")
        except IntegrityError as e:
            logger.exception(f"Erreur d'intégrité lors de la mise à jour de l'abonnement du marchand {user_id}: {e}")
            raise ConflictException(detail="Erreur lors de la mise à jour de l'abonnement (doublon ou contrainte)")
        except APIException:
            raise
        except Exception as e:
            logger.exception(f"Erreur interne lors de la mise à jour de l'abonnement du marchand {user_id}: {e}")
            raise InternalServerException(detail="Erreur interne lors de la mise à jour de l'abonnement")

    # ------------------------------
    # Suppression complète d’un marchand et (optionnel) du compte utilisateur
    # ------------------------------
    async def delete_merchant(self, user_id: str) -> MarchantSuccesRequestSchema:
        """
        Supprime un marchand et, si remove_user=True, supprime aussi le compte utilisateur.
        Utilise une transaction pour garantir l'intégrité.
        """
        try:
            async with in_transaction():
                merchant = await Merchant.get(user=user_id).prefetch_related("user")

                if merchant.user:
                    await merchant.user.delete()
                    logger.info(f"Compte utilisateur supprimé pour le marchand {user_id}")

                await merchant.delete()
                logger.info(f"Marchand supprimé : {user_id}")

            return MarchantSuccesRequestSchema(detail="Marchand supprimé avec succès")

        except DoesNotExist:
            logger.warning(f"Tentative de suppression d’un marchand inexistant : {user_id}")
            raise NotFoundException(detail="Marchand introuvable")
        except IntegrityError as e:
            logger.exception(f"Erreur d'intégrité lors de la suppression du marchand {user_id}: {e}")
            raise ConflictException(detail="Impossible de supprimer le marchand : dépendances existantes")
        except Exception as e:
            logger.exception(f"Erreur interne lors de la suppression du marchand {user_id}: {e}")
            raise InternalServerException(detail="Erreur interne lors de la suppression du marchand")

    # ------------------------------
    # Récupérer l'historique des ventes du marchand (placeholder)
    # ------------------------------
    async def get_sales_history(self, user_id: str, limit: int = 50, offset: int = 0) -> List[MarchantSaleHistorySchema]:
        """
        Retourne l'historique des ventes du marchand.
        NOTE: la logique vraie (calcul commissions, net receipts, pagination efficace)
        sera fournie par le service de ventes. Ici, on expose un format standard à retourner.
        """
        try:
            merchant = await Merchant.get(user=user_id)
            # Placeholder : tu remplaceras ceci par un appel à ton sales service / table Transaction
            # Exemple de format attendu pour chaque entrée :
            example_history = [
                {
                    "sale_id": "SALE12345",
                    "total_amount": 10000.0,
                    "commission_amount": 200.0,
                    "net_amount": 9800.0,
                    "sale_date": "2025-10-20T09:00:00Z",
                }
            ]
            return [MarchantSaleHistorySchema(**h) for h in example_history]

        except DoesNotExist:
            raise NotFoundException(detail="Marchand introuvable")
        except Exception as e:
            logger.exception(f"Erreur lors de la récupération de l'historique des ventes du marchand {user_id}: {e}")
            raise InternalServerException(detail="Erreur interne lors de la récupération de l'historique des ventes")

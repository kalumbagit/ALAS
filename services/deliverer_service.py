import random
import string
from datetime import datetime, timedelta,timezone
from tortoise.transactions import in_transaction

from tortoise.exceptions import DoesNotExist, IntegrityError
from models.user_model import DelivererDetails,DelivererEarnings,EarningStatus,User
from core.exceptions import (
    NotFoundException,
    ConflictException,
    InternalServerException,
    APIException
)
from core.logging import logger
from services.user_service import UserService
from schemas.deliverer_schema import (
    DelivererCreateSchema,
    UserOutSchema,
    DelivererDetailsOutputSchema,
    DelivererStatusUpdateSchema,
    DelivererSuspensionActiveSchema,
    DelivererSuspensionDesactivateSchema,
    DelivererSuccesRequestSchema,
    DelivererReferralHistorySchema,
    DelivererEarningsSchema,
    DelivererEarningsCreateEventSchema,
    DelivererEarningsStatusChangeSchema,
    DelivererUpdateSchema

    )


class DelivererService:
    """
    Service complet pour la gestion des livreurs.
    """
    def __init__(self):
        # Injection du UserService pour éviter la duplication de logique
        self.user_service = UserService()

    # ------------------------------
    # Générer un code de parrainage unique
    # ------------------------------
    async def generate_unique_referral_code(self, length: int = 8) -> str:
        for _ in range(10):
            code = "".join(random.choices(string.ascii_uppercase + string.digits, k=length))
            exists = await DelivererDetails.filter(referral_code=code).exists()
            if not exists:
                return code
        raise InternalServerException(detail="Impossible de générer un code de parrainage unique.")
    
    # ------------------------------
    # Création d'un livreur + création du User associé
    # ------------------------------
    async def create_deliverer(
        self,
        delivererInput: DelivererCreateSchema
    ) -> DelivererSuccesRequestSchema:
        try:
            # Vérifie si l'utilisateur existe déjà
            user= await self.user_service.create_user(delivererInput.user_data)

            # Récupère l'instance Tortoise correspondante
            user_model = await User.get(id=user.id)

            # Génère un code de parrainage unique
            referral_code = await self.generate_unique_referral_code()

            deliverer = await DelivererDetails.create(
                user=user_model,
                referral_code=referral_code,
                **delivererInput.details.dict()
            )

            # Gestion du sponsor via la méthode interne register_referral
            if delivererInput.details.sponsor_code:
                try:
                    sponsor = await DelivererDetails.get(referral_code=delivererInput.details.sponsor_code)
                    await sponsor.register_referral(deliverer)
                except DoesNotExist:
                    # Logguer un message informatif au lieu de lever une exception
                    logger.warning(f"Le code sponsor '{delivererInput.details.sponsor_code}' est incorrect. "
                               f"Le livreur a été créé sans parrain.")

            logger.info(f"Livreur créé avec succès : {deliverer.id}")
            return DelivererSuccesRequestSchema(detail="livreur creé avec succes")

        except DoesNotExist:
            raise NotFoundException(detail="Sponsor introuvable")
        except IntegrityError as e:
            logger.exception(f"Erreur d'intégrité lors de la création du livreur: {e}")
            raise ConflictException(detail="Erreur lors de la création du livreur")
        except Exception as e:
            logger.exception(f"Erreur interne lors de la création du livreur: {e}")
            raise InternalServerException(detail="Erreur interne lors de la création du livreur")

    # ------------------------------
    # Récupérer un livreur par ID du user associé
    # ------------------------------
    async def get_deliverer(self, user_id: str) -> DelivererDetailsOutputSchema:
        """
        Récupère les détails d’un livreur à partir de l’ID de son compte utilisateur.
        Retourne un schéma combiné pour le tableau de bord du livreur.
        """
        try:
            # 🔹 Récupération du livreur et des infos liées à l'utilisateur
            deliverer = await DelivererDetails.get(user=user_id).prefetch_related("user")

            # 🔹 Conversion du user en schéma de sortie
            user_data = UserOutSchema.from_orm(deliverer.user)

            # 🔹 Construction du schéma de sortie complet
            return DelivererDetailsOutputSchema(
                user_data=user_data,
                vehicle_type=deliverer.vehicle_type,
                total_earnings=deliverer.total_earnings,
                referral_earnings=deliverer.referral_earnings,
                completed_deliveries=deliverer.completed_deliveries,
                total_referals= await deliverer.get_referral_count()
            )

        except DoesNotExist:
            raise NotFoundException(detail="Livreur introuvable")
        except Exception as e:
            logger.exception(f"Erreur lors de la récupération du livreur: {e}")
            raise InternalServerException(detail="Erreur interne lors de la récupération du livreur")

    # ------------------------------
    # 📜 Liste des livreurs avec pagination
    # ------------------------------
    async def list_deliverers(
        self,
        limit: int = 50,
        offset: int = 0
    ) -> list[DelivererDetailsOutputSchema]:
        """
        Récupère la liste paginée des livreurs avec leurs informations principales.
        
        Args:
            limit (int): Nombre maximum de résultats à retourner.
            offset (int): Décalage pour la pagination.
            
        Returns:
            list[DelivererDetailsOutputSchema]: Liste des livreurs formatée selon le schéma de sortie.
        """
        try:
            deliverers = (
                await DelivererDetails.all()
                .limit(limit)
                .offset(offset)
                .prefetch_related("user")
            )

            # Transformation vers le schéma de sortie
            result = [
                DelivererDetailsOutputSchema(
                    user_data=UserOutSchema.from_orm(deliverer.user),
                    vehicle_type=deliverer.vehicle_type,
                    total_earnings=deliverer.total_earnings,
                    referral_earnings=deliverer.referral_earnings,
                    completed_deliveries=deliverer.completed_deliveries,
                    total_referals= await deliverer.get_referral_count()
                )
                for deliverer in deliverers
            ]

            return result

        except Exception as e:
            logger.exception(f"Erreur lors de la récupération de la liste des livreurs : {e}")
            raise InternalServerException(
                detail="Impossible de récupérer la liste des livreurs pour le moment."
            )


    # ------------------------------
    # Mise à jour partielle
    # ------------------------------
    async def update_deliverer(self, user_id: str, data: DelivererUpdateSchema) -> DelivererSuccesRequestSchema:
        """
        Met à jour partiellement les informations d’un livreur et retourne
        un schéma complet mis à jour.
        """
        try:
            # 🔹 Récupération du livreur avec relation user
            deliverer = await DelivererDetails.get(user=user_id).prefetch_related("user")

            # --- 🔸 Mise à jour des infos DelivererDetails ---
            update_data = data.dict(exclude_unset=True)
            for key, value in update_data.items():
                if hasattr(deliverer, key):
                    setattr(deliverer, key, value)

            
            await deliverer.save()

            # 🔹 Conversion ORM → Schéma
            user_data = UserOutSchema.from_orm(deliverer.user)

            return DelivererSuccesRequestSchema(detail="livreur mis à jour avec succès")

        except DoesNotExist:
            raise NotFoundException(detail="Livreur introuvable")
        except Exception as e:
            logger.exception(f"Erreur lors de la mise à jour du livreur ({user_id}): {e}")
            raise InternalServerException(detail="Erreur interne lors de la mise à jour du livreur")

    # ------------------------------
    # Suppression complète d’un livreur et de son compte utilisateur
    # ------------------------------
    async def delete_deliverer(self, user_id: str) -> bool:
        """
        Supprime un livreur et, si applicable, son compte utilisateur associé.
        """
        try:
            async with in_transaction():
                deliverer = await DelivererDetails.get(user=user_id).prefetch_related("user")

                # ⚠️ Optionnel : Supprimer aussi le compte utilisateur associé
                if deliverer.user:
                    await deliverer.user.delete()
                    logger.info(f"Compte utilisateur supprimé pour le livreur {user_id}")

                await deliverer.delete()
                logger.info(f"Livreur supprimé : {user_id}")

            return True

        except DoesNotExist:
            logger.warning(f"Tentative de suppression d’un livreur inexistant : {user_id}")
            raise NotFoundException(detail="Livreur introuvable")
        except IntegrityError as e:
            logger.error(f"Erreur d’intégrité lors de la suppression du livreur {user_id}: {e}")
            raise ConflictException(detail="Impossible de supprimer le livreur : dépendances existantes")
        except Exception as e:
            logger.exception(f"Erreur interne lors de la suppression du livreur {user_id}: {e}")
            raise InternalServerException(detail="Erreur interne lors de la suppression du livreur")

    # ------------------------------
    # Mise en ligne / hors ligne
    # ------------------------------
    async def set_online_status(self, user_id: str, online: bool) -> DelivererStatusUpdateSchema:
        """
        Change le statut en ligne d’un livreur.
        """
        try:
            deliverer = await DelivererDetails.get(user=user_id)
            if online:
                await deliverer.go_online()
            else:
                await deliverer.go_offline()

            logger.info(f"Livreur {user_id} {'en ligne' if online else 'hors ligne'}")
            return DelivererStatusUpdateSchema(is_online=deliverer.is_online)

        except DoesNotExist:
            raise NotFoundException(detail="Livreur introuvable")
        except Exception as e:
            logger.exception(f"Erreur lors du changement de statut pour {user_id}: {e}")
            raise InternalServerException(detail="Erreur interne lors de la mise à jour du statut")

    # ------------------------------
    # Vérification identité
    # ------------------------------
    async def verify_identity(self, user_id: str, admin_identifier: str) -> dict:
        """
        Vérifie l'identité d'un livreur en utilisant la méthode interne.
        """
        try:
            deliverer = await DelivererDetails.get(user=user_id)
            return await deliverer.verify_identity(admin_identifier)

        except DoesNotExist:
            raise NotFoundException(detail="Livreur introuvable")
        except Exception as e:
            logger.exception(f"Erreur lors de la vérification identité pour {deliverer.id}: {e}")
            raise InternalServerException(detail="Erreur interne lors de la vérification identité")

    # ------------------------------
    # Suspension d’un livreur
    # ------------------------------
    async def suspend_deliverer(self, user_id: str, days: int, reason: str) -> DelivererSuspensionActiveSchema:
        """
        Suspend temporairement un livreur pour une durée donnée.
        """
        try:
            deliverer = await DelivererDetails.get(user=user_id)
            if deliverer.is_suspended:
                raise ConflictException(detail="Le livreur est déjà suspendu")

            deliverer.is_suspended = True
            deliverer.suspension_reason = reason
            deliverer.suspension_end = datetime.now(timezone.utc) + timedelta(days=days)
            deliverer.is_online = False  # on force hors ligne

            await deliverer.save()

            logger.info(f"Livreur {user_id} suspendu pour {days} jours ({reason})")
            return DelivererSuspensionActiveSchema(
                is_suspended=True,
                suspension_raison=reason,
                suspension_end=deliverer.suspension_end
            )

        except DoesNotExist:
            raise NotFoundException(detail="Livreur introuvable")
        except ConflictException:
            raise
        except Exception as e:
            logger.exception(f"Erreur lors de la suspension du livreur {user_id}: {e}")
            raise InternalServerException(detail="Erreur interne lors de la suspension du livreur")

    # ------------------------------
    # Réactivation d’un livreur
    # ------------------------------
    async def reactivate_deliverer(self, user_id: str) -> DelivererSuspensionDesactivateSchema:
        """
        Réactive un livreur suspendu.
        """
        try:
            deliverer = await DelivererDetails.get(user=user_id)

            if not deliverer.is_suspended:
                raise ConflictException(detail="Le livreur n’est pas suspendu")

            deliverer.is_suspended = False
            deliverer.suspension_reason = None
            deliverer.suspension_end = None
            await deliverer.save()

            logger.info(f"Livreur {user_id} réactivé avec succès")
            return DelivererSuspensionDesactivateSchema(detail="Livreur réactivé avec succès")

        except DoesNotExist:
            raise NotFoundException(detail="Livreur introuvable")
        except ConflictException:
            raise
        except Exception as e:
            logger.exception(f"Erreur lors de la réactivation du livreur {user_id}: {e}")
            raise InternalServerException(detail="Erreur interne lors de la réactivation du livreur")

    # ------------------------------
    # Mise à jour des gains
    # ------------------------------
    async def add_delivery_earning(
        self,
        deliverer_earnings:DelivererEarningsCreateEventSchema
    ) -> DelivererEarningsSchema:
        """
        Ajoute un gain lié à une livraison pour un livreur.
        - Si paiement à l'avance : le gain reste PENDING jusqu'à confirmation de livraison.
        - Si livraison completé : le gain est ajouté au total_earnings et statut COMPLETED.
        """
        try:
            if deliverer_earnings.amount <= 0:
                raise ValueError("Le montant doit être positif")

            deliverer = await DelivererDetails.get(id=deliverer_earnings.deliverer_id)

            # securité pour eviter les doublons de references et enticiper sur des erreurs du type integrity
            existing = await DelivererEarnings.filter(delivery_reference=deliverer_earnings.delivery_reference).first()
            if existing:
                raise APIException(detail="Une transaction existe déjà pour cette livraison")



            # Création d’un enregistrement détaillé
            earning = await DelivererEarnings.create(
                deliverer=deliverer,
                amount=deliverer_earnings.amount,
                is_advance_payment=deliverer_earnings.is_advance_payment,
                description=deliverer_earnings.description or "Gain lié à une livraison",
                delivery_reference=deliverer_earnings.delivery_reference
            )

            logger.info(f"Gains ajoutés à {deliverer_earnings.deliverer_id} : +{deliverer_earnings.amount} ")

            return DelivererEarningsSchema(
                id=str(earning.id),
                amount=float(earning.amount),
                description=earning.description,
                status=earning.status,
                payment_date=earning.payment_date,
                is_advance_payment=earning.is_advance_payment,
                total_earnings=deliverer.total_earnings,
                referral_earnings=deliverer.referral_earnings,
                delivery_reference=earning.delivery_reference
            )

        except DoesNotExist:
            raise NotFoundException(detail="Livreur introuvable")
        except ValueError as e:
            raise APIException(detail=str(e))
        except Exception as e:
            logger.exception(
                f"Erreur lors de la mise à jour des gains du livreur {deliverer_earnings.deliverer_id}: {e}"
            )
            raise InternalServerException(detail="Erreur interne lors de la mise à jour des gains")

    async def confirm_delivery_earning(self, earning_status:DelivererEarningsStatusChangeSchema) -> DelivererEarningsSchema:
        """
        Confirme un gain lié à une livraison.
        - Met le statut à COMPLETED pour marquer que la livraison est terminé et le livreur recupere son gains.
        - Ajoute le montant au total_earnings du livreur
        """
        try:
            earning = await DelivererEarnings.get(id=earning_status.earning_id,delivery_reference=earning_status.delivery_reference).prefetch_related("deliverer")

            if earning.status == EarningStatus.COMPLETED:
                raise APIException(detail="Le gain est déjà accordé")
            if earning.status == EarningStatus.CANCELLED:
                raise APIException(detail="Le gain a été annulé, impossible de confirmer")

            earning.status = EarningStatus.COMPLETED
            await earning.save()

            # Mise à jour du total du livreur
            deliverer = earning.deliverer
            deliverer.total_earnings += float(earning.amount)
            await deliverer.save()

            logger.info(f"Gains confirmés pour {deliverer.id} : +{earning.amount}")
            return DelivererEarningsSchema(
                id=str(earning.id),
                amount=float(earning.amount),
                description=earning.description,
                status=earning.status,
                payment_date=earning.payment_date,
                is_advance_payment=earning.is_advance_payment,
                total_earnings=deliverer.total_earnings,
                referral_earnings=deliverer.referral_earnings,
                delivery_reference=earning.delivery_reference
            )

        except DoesNotExist:
            raise NotFoundException(detail="Gain introuvable")
        except Exception as e:
            logger.exception(f"Erreur lors de la confirmation du gain {earning_status.earning_id}: {e}")
            raise InternalServerException(detail="Erreur interne lors de la confirmation du gain")

    async def cancel_delivery_earning(self, earning_status:DelivererEarningsStatusChangeSchema) -> DelivererEarningsSchema:
        """
        Annule un gain lié à une livraison payée à l'avance.
        - Met le statut à CANCELLED
        - Le montant n'est pas ajouté au total_earnings
        - Optionnel : prévoir le remboursement au client côté événement externe
        """
        try:
            earning = await DelivererEarnings.get(id=earning_status.earning_id,delivery_reference=earning_status.delivery_reference).prefetch_related("deliverer")

            if earning.status == EarningStatus.COMPLETED:
                raise APIException(detail="Le gain a déjà été completé, impossible d'annuler")
            if earning.status == EarningStatus.CANCELLED:
                raise APIException(detail="Le gain est déjà annulé")

            earning.status = EarningStatus.CANCELLED
            await earning.save()

            deliverer = earning.deliverer
            logger.info(f"Gains annulés pour {deliverer.id} : {earning.amount} non crédité")
            return DelivererEarningsSchema(
                id=str(earning.id),
                amount=float(earning.amount),
                description=earning.description,
                status=earning.status,
                payment_date=earning.payment_date,
                is_advance_payment=earning.is_advance_payment,
                total_earnings=deliverer.total_earnings,
                referral_earnings=deliverer.referral_earnings,
                delivery_reference=earning.delivery_reference
            )

        except DoesNotExist:
            raise NotFoundException(detail="Gain introuvable")
        except Exception as e:
            logger.exception(f"Erreur lors de l'annulation du gain {earning_status.earning_id}: {e}")
            raise InternalServerException(detail="Erreur interne lors de l'annulation du gain")

    # ------------------------------
    # Incrémentation des livraisons complétées
    # ------------------------------
    async def increment_deliveries(self, deliverer_id: str) -> DelivererSuccesRequestSchema:
        """
        Incrémente le compteur de livraisons terminées pour un livreur.
        """
        try:
            deliverer = await DelivererDetails.get(id=deliverer_id)
            deliverer.completed_deliveries = (deliverer.completed_deliveries or 0) + 1
            await deliverer.save()

            logger.info(f"Livraison complétée enregistrée pour le livreur {deliverer_id}")
            return DelivererSuccesRequestSchema(detail="Livraison enregistrée avec succès")

        except DoesNotExist:
            raise NotFoundException(detail="Livreur introuvable")
        except Exception as e:
            logger.exception(f"Erreur lors de l'incrémentation des livraisons du livreur {deliverer_id}: {e}")
            raise InternalServerException(detail="Erreur interne lors de l'incrémentation des livraisons")

    # ------------------------------
    # Historique des filleuls
    # ------------------------------
    async def get_referral_history(self, user_id: str) -> list[DelivererReferralHistorySchema]:
        """
        Retourne l'historique des filleuls d'un livreur.
        """
        try:
            deliverer = await DelivererDetails.get(user=user_id)
            history = await deliverer.get_referral_history()
            return [DelivererReferralHistorySchema(**h) for h in history]

        except DoesNotExist:
            raise NotFoundException(detail="Livreur introuvable")
        except Exception as e:
            logger.exception(f"Erreur lors de la récupération de l'historique des filleuls: {e}")
            raise InternalServerException(detail="Erreur interne lors de la récupération de l'historique")


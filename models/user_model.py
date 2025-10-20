"""
models/user.py
Définit les modèles principaux liés aux utilisateurs, marchands et livreurs.
Chaque modèle est géré par Tortoise ORM et suit une approche normalisée.
"""

from tortoise.models import Model
from tortoise import fields
from core.enums import (
    UserType, 
    SubscriptionPlanType,
    BusinessType,
    VehicleType,
    IdentityType,
    VerificationMethod,
    EarningStatus,
    CURENCY,
    WithdrawalStatus,
    WithdrawalMethod
)
from datetime import datetime,timezone

# ==============================
# 👤 Utilisateur principal
# ==============================
class User(Model):
    """
    Représente un utilisateur de la plateforme (client, livreur, marchand, admin).
    """
    id = fields.UUIDField(pk=True)
    email = fields.CharField(max_length=254, unique=True)  # Email unique pour l'identification
    phone = fields.CharField(max_length=15, unique=True)
    password_hash = fields.CharField(max_length=128)
    first_name = fields.CharField(max_length=30)
    last_name = fields.CharField(max_length=30)
    user_type = fields.CharEnumField(UserType, default=UserType.CUSTOMER)
    avatar_url = fields.CharField(max_length=255, null=True)
    is_verified = fields.BooleanField(default=True)
    is_active = fields.BooleanField(default=True)
    is_superuser = fields.BooleanField(default=False)
    rating = fields.FloatField(default=0.0)
    total_ratings = fields.IntField(default=0)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.user_type})"

# ==============================
# 📍 Localisation utilisateur
# ==============================
class UserLocation(Model):
    """
    Stocke les adresses associées à un utilisateur (livraison, facturation...).
    """
    id = fields.UUIDField(pk=True)
    address = fields.TextField()
    city = fields.CharField(max_length=100)
    postal_code = fields.CharField(max_length=20)
    country = fields.CharField(max_length=50)
    latitude = fields.FloatField()
    longitude = fields.FloatField()
    user = fields.ForeignKeyField("models.User", related_name="locations")
    is_primary = fields.BooleanField(default=False)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    def __str__(self):
        return f"{self.address}, {self.city}"


# ==============================
# 🏪 Marchand (commerçant)
# ==============================
class Merchant(Model):
    """
    Représente un marchand enregistré dans la plateforme.
    """
    id = fields.UUIDField(pk=True)
    business_name = fields.CharField(max_length=100)
    business_type = fields.CharEnumField(BusinessType, default=BusinessType.OTHER)
    description = fields.TextField(null=True)
    logo_url = fields.CharField(max_length=255, null=True)
    banner_url = fields.CharField(max_length=255, null=True)
    siret = fields.CharField(max_length=50, unique=True)
    
    # ⚡ Nouveaux champs liés à la monétisation
    subscription_plan = fields.ForeignKeyField(
        "models.SubscriptionPlan",
        related_name="merchants",
        null=True
    )
    commission_balance = fields.FloatField(default=0.0, description="Total des commissions dues/non payées")
    last_payment_date = fields.DatetimeField(null=True)

    # ⚙️ Infos opérationnelles
    is_approved = fields.BooleanField(default=False)
    is_verified = fields.BooleanField(default=False)
    rating = fields.FloatField(default=0.0)
    total_ratings = fields.IntField(default=0)
    is_active = fields.BooleanField(default=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)
    verified_by = fields.CharField(max_length=100, null=True)
    verification_date = fields.DatetimeField(null=True)
    
    user = fields.ForeignKeyField("models.User", related_name="merchant", unique=True)

    def __str__(self):
        return f"{self.business_name} ({self.business_type})"
    
    def give_rating(self, new_rating: float):
        total_score = self.rating * self.total_ratings
        total_score += new_rating
        self.total_ratings += 1
        self.rating = total_score / self.total_ratings

    def remove_rating(self, removed_rating: float):
        if self.total_ratings <= 1:
            self.rating = 0.0
            self.total_ratings = 0
            return
        total_score = self.rating * self.total_ratings
        total_score -= removed_rating
        self.total_ratings -= 1
        self.rating = total_score / self.total_ratings

    # -----------------------
    # 🧾 Vérification identité
    # -----------------------
    async def verify_identity(self, admin_identifier: str):
        """
        Valide manuellement l’identité du marchant après évaluation humaine.
        """
        if not self.banner_url:
            raise ValueError("Piece d'identification non fourni.")
        
        self.is_verified = True
        self.is_approved = True
        self.verified_by = admin_identifier
        self.verification_date = datetime.now(timezone.utc)
        await self.save()
        return {"identity_verified": True}
# ==============================
# 🚴‍♂️ Détails du livreur
# ==============================
class DelivererDetails(Model):
    """
    Contient les informations supplémentaires relatives à un livreur.
    """

    id = fields.UUIDField(pk=True)

    # Statut et activité
    is_online = fields.BooleanField(default=False)
    is_active = fields.BooleanField(default=True)
    is_suspended = fields.BooleanField(default=False)
    suspension_end = fields.DatetimeField(null=True)
    suspension_reason = fields.TextField(null=True)

    # Informations sur les gains
    total_earnings = fields.FloatField(default=0.0) # 💰 gains liés aux livraisons
    referral_earnings = fields.FloatField(default=0.0)  # 💰 gains liés au parrainage
    completed_deliveries = fields.IntField(default=0)

    # Vérification d'identité
    identity_type = fields.CharEnumField(enum_type=IdentityType, default=IdentityType.OTHER)
    identity_document_url = fields.CharField(max_length=255, null=True)
    selfie_photo_url = fields.CharField(max_length=255, null=True)
    identity_code = fields.CharField(max_length=100, null=True)
    identity_verified = fields.BooleanField(default=False)
    verification_method = fields.CharEnumField(enum_type=VerificationMethod, default=VerificationMethod.MANUAL)
    verified_by = fields.CharField(max_length=100, null=True)
    verification_date = fields.DatetimeField(null=True)

    # Localisation et véhicule
    vehicle_type = fields.CharEnumField(enum_type=VehicleType, default=VehicleType.WALKING)
    current_latitude = fields.DecimalField(max_digits=9, decimal_places=6, null=True)
    current_longitude = fields.DecimalField(max_digits=9, decimal_places=6, null=True)

    # Parrainage (self-relation)
    sponsor = fields.ForeignKeyField(
        "models.DelivererDetails",
        related_name="referrals",
        null=True,
        on_delete=fields.SET_NULL,
    )
    referral_code = fields.CharField(max_length=20, unique=True, null=True)
    total_referrals = fields.IntField(default=0)

    # ---- Retraits du livreur ----
    pending_withdrawal_amount = fields.FloatField(default=0.0, description="Montant total en attente de retrait")
    total_withdrawn = fields.FloatField(default=0.0, description="Montant total déjà retiré")

    # Métadonnées
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)
    last_online_update=fields.DatetimeField(auto_now=True)

    # Relation principale
    user = fields.ForeignKeyField(
        "models.User", related_name="deliverer_details", unique=True
    )

    # -----------------------
    # ⚙️ Méthodes de statut
    # -----------------------
    async def go_online(self):
        """
        Met le livreur en ligne s’il est vérifié et non suspendu.
        """
        if self.is_suspended:
            raise ValueError("Impossible de se mettre en ligne : le compte est suspendu.")
        if not self.identity_verified:
            raise ValueError("Impossible de se mettre en ligne : identité non vérifiée.")
        self.is_online = True
        await self.save()
        return {"online": True}

    async def go_offline(self):
        """
        Met le livreur hors ligne.
        """
        self.is_online = False
        await self.save()
        return {"online": False}

    # -----------------------
    # 🧾 Vérification identité
    # -----------------------
    async def verify_identity(self, admin_identifier: str):
        """
        Valide manuellement l’identité du livreur après évaluation humaine.
        """
        if not self.identity_document_url or not self.selfie_photo_url:
            raise ValueError("Pièce d’identité ou photo de visage manquante.")
        
        self.identity_verified = True
        self.verification_method = VerificationMethod.MANUAL
        self.verified_by = admin_identifier
        self.verification_date = datetime.now(timezone.utc)
        await self.save()
        return {"identity_verified": True}

    #---------------------------------
    # solde disponible
    #---------------------------------
    @property
    def available_balance(self) -> float:
        """
        Solde disponible pour retrait :
        total_earnings - (total_withdrawn + pending_withdrawal_amount)
        """
        return max(self.total_earnings - (self.total_withdrawn + self.pending_withdrawal_amount), 0.0)

    # -----------------------
    # 🤝 Gestion des parrainages
    # -----------------------
    async def register_referral(self, new_deliverer: "DelivererDetails"):
        """
        Enregistre un nouveau filleul pour ce livreur et attribue la prime de parrainage.
        """
        if new_deliverer.id == self.id:
            raise ValueError("Un livreur ne peut pas se parrainer lui-même.")

        new_deliverer.sponsor = self
        await new_deliverer.save()

        # Prime de parrainage
        self.total_referrals += 1
        bonus = 100.0
        self.referral_earnings += bonus
        await self.save()

        return {"bonus": bonus, "total_referrals": self.total_referrals}

    async def get_referral_history(self):
        """
        Retourne la liste des filleuls parrainés par ce livreur.
        """
        referrals = await DelivererDetails.filter(sponsor=self).prefetch_related("user")
        return [
            {
                "id": r.id,
                "name": f"{r.user.first_name} {r.user.last_name}",
                "date": r.created_at,
                "verified": r.identity_verified,
            }
            for r in referrals
        ]

    async def get_referral_count(self):
        """Retourne le nombre de filleuls."""
        return await DelivererDetails.filter(sponsor=self).count()


    def __str__(self):
        return f"Livreur: {self.user.first_name} ({self.vehicle_type})"

# ==============================
# 💰 Gains du livreur
# ==============================
class DelivererEarnings(Model):
    """
    Représente les gains du livreur, incluant les paiements anticipés,
    les bonus et le statut du règlement.
    """
    id = fields.UUIDField(pk=True)

    deliverer = fields.ForeignKeyField(
        "models.DelivererDetails",
        related_name="earnings",
        on_delete=fields.CASCADE
    )

    # Référence vers la livraison (sans liaison directe)
    delivery_reference = fields.CharField(
        max_length=100,
        null=True,
        unique=True,  # 👉 garantit qu'une même livraison ne crée pas deux transactions
        description="Identifiant de la livraison associée (non lié directement)"
    )

    amount = fields.DecimalField(max_digits=10, decimal_places=2)
    is_advance_payment = fields.BooleanField(default=False, description="True si payé à l'avance")
    description = fields.TextField(null=True, description="Motif ou détail du paiement")
    status = fields.CharEnumField(
        enum_type=VehicleType, 
        default=EarningStatus.PENDING,
        description="Statut du paiement"
    )
    
    payment_date = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    def __str__(self):
        return f"{self.deliverer.user.first_name} - {self.amount} {CURENCY} ({'avance' if self.is_advance_payment else 'normal'})"

#===============================
# retraits du livreurs
#===============================
class DelivererWithdrawal(Model):
    """
    Historique des retraits effectués par un livreur.
    Chaque retrait représente une transaction sortante validée.
    """
    id = fields.UUIDField(pk=True)
    deliverer = fields.ForeignKeyField(
        "models.DelivererDetails",
        related_name="withdrawals",
        on_delete=fields.CASCADE
    )
    amount = fields.DecimalField(max_digits=10, decimal_places=2)
    reference = fields.CharField(max_length=100, unique=True, description="Référence unique du retrait")
    status = fields.CharEnumField(
        enum_type=WithdrawalStatus,
        default=WithdrawalStatus.PENDING,
        description="Statut du retrait"
    )
    method = fields.CharEnumField(
        enum_type=WithdrawalMethod,
        default=WithdrawalMethod.MOBILE_MONEY,
        description="Méthode de retrait utilisée"
    )
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)
    processed_at = fields.DatetimeField(null=True, description="Date effective du retrait")

    def __str__(self):
        return f"Retrait {self.reference} - {self.amount} ({self.status})"

# ==============================
# 📦 Plan d'abonnement marchand
# ==============================
class SubscriptionPlan(Model):
    """
    Modèle représentant un plan d'abonnement disponible pour les marchands.

    ⚙️ Ce modèle est lié à l'enum SubscriptionPlanType :
    - Chaque plan possède un code unique (ex: 'free', 'basic', 'pro', 'premium')
    - Le backend peut automatiquement synchroniser les valeurs de l'enum dans cette table
      via un script de "seeding" au démarrage.
    """

    id = fields.UUIDField(pk=True)

    # Code unique correspondant au type d’abonnement (doit venir de SubscriptionPlanType)
    code = fields.CharField(max_length=50, unique=True, description="Code interne du plan (ex: free, basic, pro...)")

    # Nom du plan (affichage utilisateur, ex: 'Basique', 'Premium')
    name = fields.CharField(max_length=100, description="Nom lisible du plan")

    # Description libre pour expliquer les avantages du plan
    description = fields.TextField(null=True, description="Description du plan d’abonnement")

    # Pourcentage de commission prélevé sur chaque vente
    commission_rate = fields.FloatField(default=0.0, description="Pourcentage prélevé sur chaque transaction")

    # Coût mensuel fixe du plan
    monthly_fee = fields.FloatField(default=0.0, description="Frais mensuels fixes pour ce plan")

    # Indique si le plan est actif et disponible à la sélection
    is_active = fields.BooleanField(default=True, description="Définit si le plan est actuellement actif")

    # Métadonnées temporelles
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "subscription_plans"
        ordering = ["monthly_fee"]

    def __str__(self):
        """
        Retourne une représentation lisible du plan (utile dans les logs et l’admin).
        """
        return f"{self.name} ({self.monthly_fee} FCFA/mois, {self.commission_rate*100:.1f}% commission)"

    @classmethod
    async def seed_from_enum(cls):
        """
        Synchronise automatiquement la table avec les valeurs de l'enum SubscriptionPlanType.
        (à appeler au démarrage de l'application si nécessaire)
        """
        for plan_type in SubscriptionPlanType:
            existing = await cls.get_or_none(code=plan_type.value)
            if not existing:
                await cls.create(
                    code=plan_type.value,
                    name=plan_type.label,
                    commission_rate=plan_type.commission_rate,
                    monthly_fee=plan_type.monthly_fee,
                    description=f"Plan {plan_type.label} – {plan_type.commission_rate*100:.0f}% de commission.",
                )
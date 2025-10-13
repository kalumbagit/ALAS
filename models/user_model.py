"""
models/user.py
Définit les modèles principaux liés aux utilisateurs, marchands et livreurs.
Chaque modèle est géré par Tortoise ORM et suit une approche normalisée.
"""

from tortoise.models import Model
from tortoise import fields
from core.enums import UserType, BusinessType,VehicleType,IdentityType,VerificationMethod,EarningStatus,CURENCY
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
    is_verified = fields.BooleanField(default=False)
    is_active = fields.BooleanField(default=True)
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
    is_approved = fields.BooleanField(default=False)
    is_verified = fields.BooleanField(default=False)
    rating = fields.FloatField(default=0.0)
    total_ratings = fields.IntField(default=0)
    is_active = fields.BooleanField(default=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)
    user = fields.ForeignKeyField("models.User", related_name="merchant", unique=True)

    def __str__(self):
        return f"{self.business_name} ({self.business_type})"


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
    total_earnings = fields.FloatField(default=0.0)
    referral_earnings = fields.FloatField(default=0.0)  # 💰 gains liés au parrainage
    completed_deliveries = fields.IntField(default=0)

    # Vérification d'identité
    identity_type = fields.CharEnumField(
        enum_type=IdentityType, default=IdentityType.OTHER
    )
    identity_document_url = fields.CharField(max_length=255, null=True)
    selfie_photo_url = fields.CharField(max_length=255, null=True)
    identity_code = fields.CharField(max_length=100, null=True)
    identity_verified = fields.BooleanField(default=False)
    verification_method = fields.CharEnumField(
        enum_type=VerificationMethod, default=VerificationMethod.MANUAL
    )
    verified_by = fields.CharField(max_length=100, null=True)
    verification_date = fields.DatetimeField(null=True)

    # Localisation et véhicule
    vehicle_type = fields.CharEnumField(
        enum_type=VehicleType, default=VehicleType.WALKING
    )
    current_latitude = fields.DecimalField(
        max_digits=9, decimal_places=6, null=True
    )
    current_longitude = fields.DecimalField(
        max_digits=9, decimal_places=6, null=True
    )

    # Parrainage (self-relation)
    sponsor = fields.ForeignKeyField(
        "models.DelivererDetails",
        related_name="referrals",
        null=True,
        on_delete=fields.SET_NULL,
    )
    referral_code = fields.CharField(max_length=20, unique=True, null=True)
    total_referrals = fields.IntField(default=0)

    # Métadonnées
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

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
        self.updated_at = datetime.now(timezone.utc)
        await self.save()
        return {"message": f"Le livreur {self.user.first_name} est maintenant en ligne."}

    async def go_offline(self):
        """
        Met le livreur hors ligne.
        """
        self.is_online = False
        self.updated_at = datetime.now(timezone.utc)
        await self.save()
        return {"message": f"Le livreur {self.user.first_name} est maintenant hors ligne."}

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
        self.updated_at = datetime.now(timezone.utc)
        await self.save()
        return {"message": f"Identité du livreur {self.user.first_name} vérifiée avec succès."}

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
        new_deliverer.updated_at = datetime.now(timezone.utc)
        await new_deliverer.save()

        # Prime de parrainage
        self.total_referrals += 1
        self.referral_earnings += 100.0
        self.total_earnings += 100.0
        await self.save()

        return {
            "message": f"{self.user.first_name} a parrainé {new_deliverer.user.first_name}.",
            "bonus": 100.0,
            "total_referrals": self.total_referrals,
        }

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

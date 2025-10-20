from enum import Enum

class ResponseStatus(str,Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    ERROR = "error"

class UserType (Enum):
    CUSTOMER = "customer"
    DELIVERER="deliverer"
    MERCHANT="merchant"
    ADMIN="admin"

class BusinessType(str, Enum):
    RESTAURANT = "restaurant"
    GROCERY = "grocery"
    SUPERMARKET = "supermarket"
    BOUTIQUE = "boutique"
    PHARMACY = "pharmacy"
    ELECTRONICS = "electronics"
    FASHION = "fashion"
    BEAUTY = "beauty"
    BAKERY = "bakery"
    BOOKSTORE = "bookstore"
    HARDWARE = "hardware"
    OTHER = "other"

    @property
    def label(self) -> str:
        """Libellé lisible pour affichage."""
        labels = {
            "restaurant": "Restaurant",
            "grocery": "Épicerie",
            "supermarket": "Supermarché",
            "boutique": "Boutique / Magasin",
            "pharmacy": "Pharmacie",
            "electronics": "Électronique / High-Tech",
            "fashion": "Mode / Vêtements",
            "beauty": "Beauté / Cosmétique",
            "bakery": "Boulangerie / Pâtisserie",
            "bookstore": "Librairie / Papeterie",
            "hardware": "Quincaillerie / Bricolage",
            "other": "Autre",
        }
        return labels[self.value]

    def __str__(self):
        return self.label
class SubscriptionPlanType(str, Enum):
    """
    Types d’abonnements disponibles pour les marchands.
    Chaque plan définit son coût mensuel et le taux de commission applicable.
    """

    FREE = "free"
    BASIC = "basic"
    PRO = "pro"
    PREMIUM = "premium"

    
    @property
    def label(self) -> str:
        labels = {
            "free": "Gratuit",
            "basic": "Basique",
            "pro": "Professionnel",
            "premium": "Premium",
        }
        return labels[self.value]

    @property
    def monthly_fee(self) -> float:
        fees = {
            "free": 0.0,
            "basic": 5000.0,
            "pro": 15000.0,
            "premium": 30000.0,
        }
        return fees[self.value]

    @property
    def commission_rate(self) -> float:
        rates = {
            "free": 0.10,
            "basic": 0.05,
            "pro": 0.02,
            "premium": 0.0,
        }
        return rates[self.value]

    def __str__(self):
        return f"{self.label} ({self.monthly_fee:.0f} FCFA/mois, {self.commission_rate*100:.1f}% commission)"

class VehicleType(Enum):
    BIKE="bike"
    MOTORCYCLE="motorcycle"
    CAR="car"
    WALKING="walking"
    SCOOTER="scooter"

class IdentityType(Enum):
    CNI="cni"  # Carte Nationale d'Identité
    PASSPORT="passport"
    DRIVER_LICENSE="driver_license"
    ELECTORAL_CARD="electoral_card"
    CNI_RECEIPT="recépicé de la cni"
    OTHER="other"

class VerificationMethod(Enum):
    MANUAL="manual"  # Vérification manuelle par un administrateur
    SELFIE_MATCH="selfie_match"  # Correspondance avec un selfie
    OTP_ONLY="otp_only"  # Vérification par OTP uniquement
    SPONSORED="sponsored"  # Vérification par un tiers sponsorisé

class EarningStatus(Enum):
    PENDING="pending"
    COMPLETED="completed"
    FAILED="failed"
    CANCELLED="cancelled"
    REFUNDED="refunded"
    ADJUSTED="adjusted"

CURENCY="FCFA"
    
class WithdrawalStatus(str, Enum):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    REJECTED = "REJECTED"

class WithdrawalMethod(str, Enum):
    MOBILE_MONEY = "MOBILE_MONEY"
    BANK_TRANSFER = "BANK_TRANSFER"

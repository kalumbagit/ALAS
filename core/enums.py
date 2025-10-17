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

class BusinessType(Enum) :
    RESTAURANT="restaurant"
    GROCERY="grocery"
    PHARMACY="pharmacy"
    ELECTRONICS="electronics"
    FASHION="fashion"
    OTHER="other"

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

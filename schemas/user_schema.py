from pydantic import BaseModel, EmailStr, Field,ConfigDict
from typing import Optional
from core.enums import UserType


# ----------------------
# Schéma pour création
# ----------------------
class UserCreateSchema(BaseModel):
    email: EmailStr
    phone: str = Field(..., max_length=15)
    password: str = Field(..., min_length=8,max_length=72)
    first_name: str = Field(..., max_length=30)
    last_name: str = Field(..., max_length=30)
    user_type: Optional[UserType] = UserType.CUSTOMER
    avatar_url: Optional[str]=None

# ----------------------
# Schéma pour mise à jour complète (PUT)/ partielle (PATCH)
# ----------------------
class UserUpdateSchema(BaseModel):
    """
    Schéma pour la mise à jour des données utilisateur
    """
    email: Optional[EmailStr] = None
    phone: Optional[str] =  Field(None, max_length=15)
    first_name: Optional[str] =  Field(None, max_length=30)
    last_name: Optional[str] =  Field(None, max_length=30)
    avatar_url: Optional[str] = None

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "first_name": "Nouveau prénom",
                "last_name": "Nouveau nom",
                "avatar_url": "https://example.com/avatar.jpg"
            }
        }
    )

# ----------------------
# Schéma de sortie
# ----------------------
class UserOutSchema(BaseModel):
    """
    Schéma pour les données utilisateur à exposer à l'API
    (Uniquement les données utiles pour la consommation)
    """
    id: str
    email: EmailStr 
    phone: str
    first_name: str
    last_name: str
    user_type: UserType
    avatar_url: Optional[str] = None
    rating: float
    total_ratings: int

    model_config = ConfigDict(from_attributes=True)

    @classmethod
    def from_orm(cls, user):
        """
        Méthode utilitaire pour créer un UserData à partir d'un modèle User
        """
        return cls(
            id=str(user.id),
            email=user.email,
            phone=user.phone,
            first_name=user.first_name,
            last_name=user.last_name,
            user_type=user.user_type,
            avatar_url=user.avatar_url,
            rating=user.rating,
            total_ratings=user.total_ratings,
        )

class UserPublicSchema(BaseModel):
    """
    Schéma pour les données utilisateur publiques (moins sensibles)
    """
    id: str
    first_name: str
    last_name: str
    user_type: UserType
    avatar_url: Optional[str] = None
    rating: float
    total_ratings: int

    model_config = ConfigDict(from_attributes=True)

class LoginDataSchema(BaseModel):
    """
    Schéma pour les données de connexion
    """
    email: EmailStr
    password: str

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "email": "user@example.com",
                "password": "votre_mot_de_passe"
            }
        }
    )

class LoginResponseSchema(BaseModel):
    """
    Schéma pour la réponse de connexion
    """
    access_token: str
    refresh_token: str
    token_type: str
    user: UserOutSchema

class TokenResponseSchema(BaseModel):
    """
    Schéma pour la réponse de token
    """
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str

class RefreshTokenDataSchema(BaseModel):
    """
    Schéma pour le refresh token
    """
    refresh_token: str

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "refresh_token": "votre_refresh_token_ici"
            }
        }
    )

class UserStatusUpdateSchema(BaseModel):
    """
    Schéma pour la mise à jour du statut utilisateur
    """
    is_active: bool

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra = {
            "example": {
                "is_active": True
            }
        }
    )

class UserRatingUpdateSchema(BaseModel):
    rating: float = Field(ge=0, le=5, description="Note entre 0 et 5")

class UserExistsResponseSchema(BaseModel):
    exists: bool

class UserCountResponseSchema(BaseModel):
    count: int

class DeleteResponseSchema(BaseModel):
    message: str = Field(default="Resource deleted successfully")

# Schémas pour les réponses API avec votre système ResponseHandler
class APIUserResponse(BaseModel):
    """
    Schéma standard pour les réponses API avec données utilisateur
    """
    success: bool = True
    message: str = "Opération réussie"
    data: Optional[UserOutSchema] = None

class APIUsersResponse(BaseModel):
    """
    Schéma pour les réponses avec liste d'utilisateurs
    """
    success: bool = True
    message: str = "Opération réussie"
    data: list[UserOutSchema] = []

class APILoginResponse(BaseModel):
    """
    Schéma pour la réponse de login standardisée
    """
    success: bool = True
    message: str = "Connexion réussie"
    data: LoginResponseSchema




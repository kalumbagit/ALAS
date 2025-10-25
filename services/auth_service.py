# ==========================================
# 🧠 AuthService — version FastAPI-JWT moderne
# ==========================================

from typing import Optional

from fastapi import HTTPException
from fastapi.security import  HTTPAuthorizationCredentials
from passlib.context import CryptContext
from tortoise.exceptions import DoesNotExist, OperationalError

from models.user_model import User, DelivererDetails, Merchant, UserType
from schemas.user_schema import (
    LoginDataSchema,
    LoginResponseSchema,
    TokenResponseSchema,
    UserOutSchema,
)
from core.exceptions import UnauthorizedException, InternalServerException
from core.security import jwt, check_if_token_in_denylist, revoke_token,decode_token
from core.logging import logger


# ------------------------------
# 🔐 Contexte de hash
# ------------------------------
pwd_context = CryptContext(
    schemes=["argon2", "bcrypt"],        # ordre : argon2 préféré si présent
    default="argon2",                   # crée les nouveaux hashes avec argon2
    deprecated="auto",
    truncate_error=True,
)

class AuthService:
    """
    Service d'authentification et de gestion des tokens JWT
    """

    # ===================================================
    # 🔸 Gestion des mots de passe
    # ===================================================
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """
        Vérifie si le mot de passe correspond au hash
        """
        return pwd_context.verify(plain_password, hashed_password)

    def get_password_hash(self, password: str) -> str:
        """
        Hash un mot de passe
        """
        return pwd_context.hash(password)
    
    
    # ===================================================
    # 🔸 Authentification utilisateur
    # ===================================================
       
    async def authenticate_user(self, data:LoginDataSchema) -> Optional[User]:
        """
        Authentifie un utilisateur avec email et mot de passe
        """
        try:
            user = await User.get(email=data.email)
            if user and self.verify_password(data.password, user.password_hash):
                return user
            return None
        except DoesNotExist:
            return None
    
    # ------------------------------
    # 🧩 Vérifications internes selon type utilisateur
    # ------------------------------
    async def _validate_customer(self, user: User):
        """Validation spécifique pour un client."""
        if hasattr(user, "is_verified") and not user.is_verified:
            raise UnauthorizedException(detail="Veuillez vérifier votre adresse e-mail avant de vous connecter.")
        if hasattr(user, "is_active") and not user.is_active:
            raise UnauthorizedException(detail="Compte désactivé. Contactez l’administrateur.")

    async def _validate_deliverer(self, user: User):
        """Validation spécifique pour un livreur."""
        deliverer = await DelivererDetails.get_or_none(user=user)
        if not deliverer:
            raise UnauthorizedException(detail="Compte livreur introuvable.")
        if not deliverer.identity_verified:
            raise UnauthorizedException(detail="Votre compte livreur n’a pas encore été vérifié.")
        if deliverer.is_suspended:
            raise UnauthorizedException(detail="Votre compte livreur est suspendu.")
        if not user.is_active:
            raise UnauthorizedException(detail="Compte livreur inactif.")

    async def _validate_merchant(self, user: User):
        """Validation spécifique pour un marchand."""
        merchant = await Merchant.get_or_none(user=user)
        if not merchant:
            raise UnauthorizedException(detail="Compte marchand introuvable.")
        if not merchant.is_verified:
            raise UnauthorizedException(detail="Votre compte marchand n’a pas encore été validé.")
        if not user.is_active:
            raise UnauthorizedException(detail="Compte marchand inactif.")

    async def _validate_admin(self, user: User):
        """Validation spécifique pour un administrateur."""
        if not user.is_active:
            raise UnauthorizedException(detail="Compte administrateur désactivé.")
        if not user.is_superuser:
            raise UnauthorizedException(detail="Accès refusé : cet utilisateur n’a pas les droits administrateur.")


    async def _validate_user_by_type(self, user: User):
        """Dirige la validation vers la méthode adaptée selon le type utilisateur."""
        match user.user_type:
            case UserType.CUSTOMER:
                await self._validate_customer(user)
            case UserType.DELIVERER:
                await self._validate_deliverer(user)
            case UserType.MERCHANT:
                await self._validate_merchant(user)
            case UserType.ADMIN:
                await self._validate_admin(user)
            case _:
                raise UnauthorizedException(detail="Type d’utilisateur non reconnu.")
    
    # ------------------------------
    # Login / Logout / Refresh
    # ------------------------------
    async def login(self, data: LoginDataSchema) -> LoginResponseSchema:
        """
        Authentifie un utilisateur et génère les tokens JWT avec gestion robuste des erreurs.
        """
        try:
            # 1️⃣ Authentification basique
            user = await self.authenticate_user(data)
            if not user:
                logger.warning(f"Tentative de connexion échouée pour {data.email}")
                raise UnauthorizedException(detail="Email ou mot de passe incorrect")

            # 2️⃣ Validation selon le type d’utilisateur
            await self._validate_user_by_type(user)

            # Génération des tokens JWT
            try:
                claims_data ={"sub": str(user.id),"user_type": user.user_type.value}
                # Claims spécifiques pour merchant
                if user.user_type == UserType.MERCHANT:
                    merchant = await Merchant.get_or_none(user=user.id).prefetch_related("subscription_plan")
                    if merchant and merchant.subscription_plan:
                        claims_data["subscription_plan"] = merchant.subscription_plan.code
                    else:
                        claims_data["subscription_plan"] = 'free'  # ou "free" selon ta logique
                
                # Création des tokens
                access_token = jwt.create_access_token(claims_data)
                refresh_token = jwt.create_refresh_token({"sub": str(user.id)})
            except Exception as e:
                logger.error(f"Erreur lors de la génération du token JWT pour {data.email} : {e}")
                raise InternalServerException(detail="Erreur lors de la création du token")

            # Construction de la réponse
            user_out = UserOutSchema.from_orm(user)
            logger.info(f"Connexion réussie pour l’utilisateur : {user.email}")

            return LoginResponseSchema(
                access_token=access_token,
                refresh_token=refresh_token,
                token_type="bearer",
                user=user_out
            )

        except UnauthorizedException:
            # On relance directement nos exceptions custom
            raise

        except OperationalError as e:
            logger.error(f"Erreur de base de données pendant le login de {data.email} : {e}")
            raise InternalServerException(detail="Erreur de communication avec la base de données")
    
        except HTTPException as e:
            # On loggue, mais on relaisse passer l'exception à FastAPI
            logger.warning(f"Exception HTTP: {e.detail}")
            raise e  # 🔥 Important : ne pas la remplacer !

        except Exception as e:
            logger.exception(f"Erreur inattendue lors du login de {data.email} : {e}")
            raise InternalServerException(detail="Erreur interne lors de l’authentification")

    # ===================================================
    # 🔸 Logout complet (access + refresh)
    # ===================================================
    async def logout(self, access_token: str, refresh_token: str) -> LoginResponseSchema:
        """
        Révoque l'access token et le refresh token pour déconnexion sécurisée.
        """
        if not access_token or not refresh_token:
            raise UnauthorizedException("Tokens manquants")

        try:
            # Décodage des tokens
            access_payload = decode_token(access_token)
            refresh_payload = decode_token(refresh_token)  # refresh_token est déjà str

            # Révocation dans la denylist
            await revoke_token(access_payload["jti"], access_payload["exp"])
            await revoke_token(refresh_payload["jti"], refresh_payload["exp"])

             # Logger avec fallback si 'sub' absent
            user_id = access_payload.get("sub") or access_payload.get("subject", {}).get("sub", "inconnu")
            logger.info(f"Logout successful for user {user_id}")

            return LoginResponseSchema(detail="Déconnexion réussie, tokens révoqués")

        except UnauthorizedException as e:
            # Token invalide ou expiré
            raise e
        except Exception as e:
            logger.exception(f"Erreur interne lors du logout: {e}")
            raise InternalServerException("Erreur interne lors du logout")


    # ===================================================
    # 🔸 Refresh Token
    # ===================================================
    async def refresh(self, refresh_token: str) -> TokenResponseSchema:
        try:
            # 1️⃣ Décodage du refresh token
            try:
                payload = decode_token(refresh_token)
            except UnauthorizedException:
                raise

            # 2️⃣ Récupération de l'utilisateur
            subject_data = payload.get("subject") or {}
            user_id = subject_data.get("sub")
            if not user_id:
                raise UnauthorizedException(detail="Token invalide, 'sub' manquant")

            user = await User.get_or_none(id=user_id)
            if not user:
                raise UnauthorizedException(detail="Utilisateur introuvable")

            # 3️⃣ Vérification que le token n'est pas révoqué
            if check_if_token_in_denylist(payload):
                raise UnauthorizedException(detail="Refresh token révoqué")

            # 4️⃣ Préparation des claims pour le nouveau access token
            claims_data = {
                "sub": str(user.id),
                "user_type": user.user_type.value
            }

            # Claims spécifiques pour les merchants
            if user.user_type == UserType.MERCHANT:
                merchant = await Merchant.get_or_none(user=user.id).prefetch_related("subscription_plan")
                if merchant and merchant.subscription_plan:
                    claims_data["subscription_plan"] = merchant.subscription_plan.code
                else:
                    claims_data["subscription_plan"] = "free"

            # 5️⃣ Génération du nouveau access token
            new_access_token = jwt.create_access_token(claims_data)

            logger.info(f"Token rafraîchi pour {user.email}")

            # 6️⃣ Retour du token
            return TokenResponseSchema(
                access_token=new_access_token,
                token_type="bearer",
            )

        except Exception as e:
            logger.exception(f"Erreur refresh token : {e}")
            raise UnauthorizedException(detail="Token invalide ou expiré")


    # ===================================================
    # 🔸 Récupération de l’utilisateur courant
    # ===================================================
    async def get_current_user(self, credentials: HTTPAuthorizationCredentials) -> UserOutSchema:
        try:

            if not credentials:
                raise UnauthorizedException(detail="Token manquant")
            
            # Décodage du token
            try:
                payload = decode_token(credentials.credentials)
            except UnauthorizedException :
                raise

            subject_data = payload.get("subject") or {}
            user_id = subject_data.get("sub")
            if not user_id:
                raise UnauthorizedException(detail="Token invalide, 'sub' manquant")

            if check_if_token_in_denylist(payload):
                raise UnauthorizedException(detail="Token révoqué")

            user = await User.get_or_none(id=user_id)
            if not user or not getattr(user, "is_active", True):
                raise UnauthorizedException(detail="Utilisateur inactif ou introuvable")

            return UserOutSchema.from_orm(user)
        except Exception as e:
            logger.exception(f"Erreur récupération utilisateur courant : {e}")
            raise UnauthorizedException(detail="Erreur d’authentification")
    

# Standard library
from datetime import datetime
from typing import Optional

# Third-party libraries
from fastapi import HTTPException
from fastapi_jwt_auth import AuthJWT
from fastapi_jwt_auth.exceptions import MissingTokenError, JWTDecodeError,RevokedTokenError
from passlib.context import CryptContext
from tortoise.exceptions import DoesNotExist,OperationalError
import jwt

# Local application imports
from models.user_model import User,DelivererDetails,Merchant,UserType
from schemas.user_schema import (
    LoginDataSchema,
    LoginResponseSchema,
    TokenResponseSchema,
    UserOutSchema,
)
from core.exceptions import UnauthorizedException, InternalServerException
from core.logging import logger


# Contexte pour le hash des mots de passe
# Contexte pour le hash des mots de passe
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

    # ------------------------------
    # Gestion des mots de passe
    # ------------------------------
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
    
    
    # ------------------------------
    # Authentification utilisateur
    # ------------------------------
       
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
    async def login(self, data: LoginDataSchema,auth_jwt: AuthJWT) -> LoginResponseSchema:
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
                access_token = auth_jwt.create_access_token(
                    subject=str(user.id),
                    user_claims={"usertype": user.user_type.value}  # ajoute le type utilisateur
                )

                refresh_token = auth_jwt.create_refresh_token(
                    subject=str(user.id),
                    user_claims={"usertype": user.user_type.value}  # idem
                )
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

    async def logout(self, auth_jwt: AuthJWT,access_token: str, refresh_token: str) -> dict:
        """
        Déconnecte l'utilisateur en révoquant les deux tokens (access + refresh).
        Les deux tokens sont attendus dans les headers :
        - Authorization: Bearer <access_token>
        - X-Refresh-Token: <refresh_token>
        """
        try:

            # --------------------------------------------------------------------
            # 1️⃣ Décodage du refresh token
            # --------------------------------------------------------------------
            if not refresh_token:
                raise UnauthorizedException(detail="Refresh token manquant")

            try:
                decoded_refresh = auth_jwt._verified_token(refresh_token)
            except Exception as e:
                logger.warning(f"Refresh token invalide : {e}")
                raise UnauthorizedException(detail="Refresh token invalide ou expiré")

            refresh_jti = decoded_refresh.get("jti")
            refresh_exp = decoded_refresh.get("exp")

            if not refresh_jti or not refresh_exp:
                raise UnauthorizedException(detail="Refresh token mal formé")
            
            # --------------------------------------------------------------------
            # 2️⃣ Décodage du access token
            # --------------------------------------------------------------------
            if not access_token:
                raise UnauthorizedException(detail="Access token manquant")

            try:
                decoded_access = auth_jwt._verified_token(access_token)
            except Exception as e:
                logger.warning(f"Access token invalide : {e}")
                raise UnauthorizedException(detail="Access token invalide ou expiré")

            access_jti = decoded_access.get("jti")
            access_exp = decoded_access.get("exp")

            if not access_jti or not access_exp:
                raise UnauthorizedException(detail="Access token mal formé")

            # --------------------------------------------------------------------
            # 3️⃣ Révocation dans Redis
            # --------------------------------------------------------------------
            from core.redis import revoke_token

            # Conversion timestamps
            access_exp_ts = int(access_exp) if isinstance(access_exp, int) else int(datetime.timestamp(access_exp))
            refresh_exp_ts = int(refresh_exp) if isinstance(refresh_exp, int) else int(datetime.timestamp(refresh_exp))

            await revoke_token(access_jti, access_exp_ts)
            await revoke_token(refresh_jti, refresh_exp_ts)


            logger.info(f"✅ Tokens révoqués : access_jti={access_jti}, refresh_jti={refresh_jti}")

            return {"detail": "Déconnexion réussie, tous les tokens révoqués"}
        
        # --------------------------------------------------------------------
        # 3️⃣ Révocation dans Redis
        # --------------------------------------------------------------------

        except MissingTokenError:
            logger.warning("Tentative de déconnexion sans token JWT")
            raise UnauthorizedException(detail="Token manquant ou non fourni")
        
        except JWTDecodeError:
            logger.error("Échec du décodage du token JWT lors du logout")
            raise UnauthorizedException(detail="Token invalide ou mal formé")
        
        except UnauthorizedException:
            # Relaisse passer nos exceptions custom
            raise

        except Exception as e:
            logger.exception(f"Erreur inattendue lors du logout : {e}")
            raise InternalServerException(detail="Erreur interne lors de la déconnexion")
  
    async def refresh(self, auth_jwt: AuthJWT,refresh_token: str) -> TokenResponseSchema:
        """
        Rafraîchit le token d’accès à partir d’un refresh token valide.
        - Récupère le refresh token depuis le header `X-Refresh-Token`.
        - Vérifie s’il n’est pas révoqué.
        - Génère un nouveau access token.
        """
        try:

            # --------------------------------------------------------------------
            # 1️⃣ Vérifie la présence du refresh token dans les headers
            # --------------------------------------------------------------------
            if not refresh_token:
                raise UnauthorizedException(detail="Refresh token manquant dans les en-têtes")

            # --------------------------------------------------------------------
            # 2️⃣ Vérifie et décode le refresh token
            # --------------------------------------------------------------------
            try:
                decoded_refresh = auth_jwt._verified_token(refresh_token)
            except Exception as e:
                logger.warning(f"Refresh token invalide ou expiré : {e}")
                raise UnauthorizedException(detail="Refresh token invalide ou expiré")

            refresh_jti = decoded_refresh.get("jti")
            refresh_exp = decoded_refresh.get("exp")

            if not refresh_jti or not refresh_exp:
                raise UnauthorizedException(detail="Refresh token mal formé")

            # --------------------------------------------------------------------
            # 3️⃣ Vérifie si le refresh token est dans la denylist
            # --------------------------------------------------------------------
            from core.security import check_if_token_in_denylist
            if check_if_token_in_denylist({"jti": refresh_jti}):
                logger.warning(f"Refresh token révoqué détecté : jti={refresh_jti}")
                raise UnauthorizedException(detail="Refresh token révoqué. Veuillez vous reconnecter.")

            # --------------------------------------------------------------------
            # 4️⃣ Récupère l’utilisateur depuis le subject du token
            # --------------------------------------------------------------------
            current_user_id = decoded_refresh.get("sub")
            if not current_user_id:
                raise UnauthorizedException(detail="Token invalide ou mal formé")

            try:
                user = await User.get(id=current_user_id)
            except DoesNotExist:
                raise UnauthorizedException(detail="Utilisateur introuvable")

            # --------------------------------------------------------------------
            # 5️⃣ Génère un nouveau access token
            # --------------------------------------------------------------------
            new_access_token = auth_jwt.create_access_token(
                    subject=str(user.id),
                    user_claims={"usertype": user.user_type.value}  # ajoute le type utilisateur
                )

            logger.info(f"✅ Token rafraîchi avec succès pour {user.email}")

            return TokenResponseSchema(
                access_token=new_access_token,
                token_type="bearer"
            )

        # ------------------------------
        # Gestion fine des exceptions
        # ------------------------------
        except MissingTokenError:
            logger.warning("Tentative de rafraîchissement sans token")
            raise UnauthorizedException(detail="Aucun token fourni")

        except JWTDecodeError:
            logger.warning("Échec du décodage du refresh token")
            raise UnauthorizedException(detail="Token invalide ou expiré")

        except UnauthorizedException:
            # Relaisse passer nos exceptions custom
            raise

        except Exception as e:
            logger.exception(f"Erreur interne inattendue lors du refresh token : {e}")
            raise InternalServerException(detail="Erreur interne lors du rafraîchissement du token")

    # ------------------------------
    # Dépendance pour récupérer l'utilisateur courant
    # ------------------------------
    async def get_current_user(self, auth_jwt: AuthJWT) -> UserOutSchema:
        try:
            auth_jwt.jwt_required()
            raw_jwt = auth_jwt.get_raw_jwt()
            jti = raw_jwt.get("jti")
            user_id = auth_jwt.get_jwt_subject()

            if not jti or not user_id:
                logger.warning("Token JWT incomplet ou mal formé détecté lors de get_current_user()")
                raise UnauthorizedException(detail="Token invalide ou incomplet")

            # 🧩 Récupération de l’utilisateur en base
            try:
                user = await User.get(id=user_id)
            except DoesNotExist:
                logger.warning(f"Utilisateur introuvable pour id={user_id}")
                raise UnauthorizedException(detail="Utilisateur introuvable")

            # 🔍 Vérifie l’état du compte si applicable
            if hasattr(user, "is_active") and not user.is_active:
                logger.info(f"Accès refusé : compte inactif pour utilisateur {user.email}")
                raise UnauthorizedException(detail="Compte désactivé. Veuillez contacter l’administrateur.")

            logger.debug(f"Utilisateur courant récupéré avec succès : {user.email}")

            return UserOutSchema.from_orm(user)


       # ------------------------------
        # Gestion des erreurs JWT
        # ------------------------------
        except MissingTokenError:
            logger.warning("Tentative d’accès sans token JWT")
            raise UnauthorizedException(detail="Token non fourni")

        except RevokedTokenError as e :
            logger.warning(f"Tentative d’accès avec un token révoqué : plus de details {e.message} ")
            raise UnauthorizedException(detail=f"Token révoqué. Veuillez vous reconnecter. plus de details {e.message} ")

        except JWTDecodeError:
            logger.error("Erreur de décodage du token JWT lors de get_current_user()")
            raise UnauthorizedException(detail="Token invalide ou expiré")

        # ------------------------------
        # Gestion générique
        # ------------------------------
        except UnauthorizedException:
            raise

        except jwt.PyJWTError as e:
            logger.error(f"Erreur PyJWT inattendue lors de get_current_user() : {e}")
            raise UnauthorizedException(detail="Erreur lors de la validation du token")

        except Exception as e:
            logger.exception(f"Erreur inattendue lors de la récupération de l'utilisateur courant : {e}")
            raise InternalServerException(detail="Erreur interne lors de la récupération de l'utilisateur")

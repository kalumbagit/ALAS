# Standard library
from datetime import datetime, timezone
from typing import Dict, Optional

# Third-party libraries
from fastapi import HTTPException
from fastapi_jwt_auth import AuthJWT
from fastapi_jwt_auth.exceptions import MissingTokenError, JWTDecodeError,RevokedTokenError
from passlib.context import CryptContext
from tortoise.exceptions import DoesNotExist,OperationalError
import jwt

# Local application imports
from models.user_model import User
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
    # Login / Logout / Refresh
    # ------------------------------
    async def login(self, data: LoginDataSchema,auth_jwt: AuthJWT) -> LoginResponseSchema:
        """
        Authentifie un utilisateur et génère les tokens JWT avec gestion robuste des erreurs.
        """
        try:
            # Authentification de l'utilisateur
            user = await self.authenticate_user(data)
            if not user:
                logger.warning(f"Tentative de connexion échouée pour {data.email}")
                raise UnauthorizedException(detail="Email ou mot de passe incorrect")

            # Vérifie si le compte est actif
            if hasattr(user, "is_active") and not user.is_active:
                logger.info(f"Tentative de connexion sur compte inactif : {data.email}")
                raise UnauthorizedException(detail="Compte désactivé. Contactez l’administrateur.")

            # Vérifie si l'adresse e-mail est confirmée (si applicable)
            if hasattr(user, "is_verified") and not user.is_verified:
                logger.info(f"Connexion refusée : email non vérifié pour {data.email}")
                raise UnauthorizedException(detail="Veuillez vérifier votre adresse e-mail avant de vous connecter.")

            # Génération des tokens JWT
            try:
                access_token = auth_jwt.create_access_token(subject=str(user.id))
                refresh_token = auth_jwt.create_refresh_token(subject=str(user.id))
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

    async def logout(self, auth_jwt: AuthJWT) -> dict:
        try:
            # Vérifie la présence et la validité du refresh token
            auth_jwt.jwt_refresh_token_required()
            raw_refresh_jwt = auth_jwt.get_raw_jwt()
            refresh_jti = raw_refresh_jwt.get("jti")
            refresh_exp = raw_refresh_jwt.get("exp")

            if not refresh_jti or not refresh_exp:
                logger.warning("Tokens incomplets ou invalides lors du logout")
                raise UnauthorizedException(detail="Token(s) invalide(s)")

            # Convertir en timestamp si nécessaire
            refresh_exp_ts = int(refresh_exp) if isinstance(refresh_exp, int) else int(datetime.timestamp(refresh_exp))

            # 🔥 Stockage dans Redis ou table des tokens révoqués
            from core.redis import revoke_token
            await revoke_token(refresh_jti, refresh_exp_ts)

            logger.info(f"Tokens révoqués avec succès : refresh_jti={refresh_jti}")

            return {"detail": "Déconnexion réussie, tous les tokens révoqués"}

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
  
    async def refresh(self, auth_jwt: AuthJWT) -> TokenResponseSchema:
        """
        Rafraîchit le token d’accès à partir d’un refresh token valide.
        Vérifie également si le refresh token est révoqué.
        """
        try:
            # 🔒 Vérifie la présence du refresh token
            auth_jwt.jwt_refresh_token_required()
            raw_refresh = auth_jwt.get_raw_jwt()
            refresh_jti = raw_refresh.get("jti")

            # Vérifie si le refresh token est déjà révoqué
            from core.security import check_if_token_in_denylist
            if check_if_token_in_denylist({"jti": refresh_jti}):
                logger.warning(f"Refresh token révoqué détecté : jti={refresh_jti}")
                raise UnauthorizedException(detail="Refresh token révoqué. Veuillez vous reconnecter.")

            # Récupère l’utilisateur
            current_user_id = auth_jwt.get_jwt_subject()
            if not current_user_id:
                raise UnauthorizedException(detail="Token invalide ou mal formé")

            try:
                user = await User.get(id=current_user_id)
            except DoesNotExist:
                raise UnauthorizedException(detail="Utilisateur introuvable")

            # Génère un nouveau access token
            new_access_token = auth_jwt.create_access_token(subject=str(user.id))
            logger.info(f"Token rafraîchi avec succès pour {user.email}")

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

        except RevokedTokenError:
            logger.warning("Tentative d’utilisation d’un refresh token révoqué")
            raise UnauthorizedException(detail="Token révoqué. Veuillez vous reconnecter.")

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

            # Vérification via Redis
            from core.redis import is_token_revoked
            if await is_token_revoked(jti):
                logger.warning(f"Tentative d’accès avec un token révoqué : jti={jti}")
                raise UnauthorizedException(detail="Token révoqué. Veuillez vous reconnecter.")

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
            logger.warning(f"Tentative d’accès avec un token révoqué : plus de details {e} ")
            raise UnauthorizedException(detail=f"Token révoqué. Veuillez vous reconnecter. plus de details {e}")

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

from models.user_model import User
from typing import List, Optional
from tortoise.exceptions import DoesNotExist, IntegrityError, ValidationError
from fastapi import HTTPException
from tortoise.transactions import in_transaction
from schemas.user_schema import (
    UserCreateSchema, 
    UserUpdateSchema, 
    UserOutSchema, 
    UserStatusUpdateSchema,
    UserCountResponseSchema,
    UserExistsResponseSchema,
    DeleteResponseSchema
    )
from passlib.context import CryptContext
from core.enums import UserType
from core.exceptions import (
    APIException, 
    NotFoundException, 
    ConflictException, 
    InternalServerException
)
from core.logging import logger

import uuid

# Contexte pour le hash des mots de passe
pwd_context = CryptContext(
    schemes=["argon2", "bcrypt"],        # ordre : argon2 préféré si présent
    default="argon2",                   # crée les nouveaux hashes avec argon2
    deprecated="auto",
    truncate_error=True,
)

class UserService:
    """
    Service professionnel de gestion des utilisateurs avec gestion robuste des exceptions
    """

    def __init__(self):
        self.model = User
    
    def _hash_password(self, password: str) -> str:
        max_len_bytes = 72
        password_bytes = password.encode('utf-8')
        if len(password_bytes) > max_len_bytes:
            logger.warning("Le mot de passe dépasse 72 bytes, il sera tronqué pour bcrypt.")
            password_bytes = password_bytes[:max_len_bytes]
        return pwd_context.hash(password_bytes)

    async def _validate_user_data(self, user_data: UserCreateSchema) -> None:
        """
        Validation métier des données utilisateur
        """
        # Validation de l'email
        if await User.filter(email=user_data.email).exists():
            raise ConflictException(detail=f"L'email {user_data.email} est déjà utilisé")
        
        # Validation du téléphone
        if await User.filter(phone=user_data.phone).exists():
            raise ConflictException(detail=f"Le téléphone {user_data.phone} est déjà utilisé")
        
    async def create_user(self, user_data: UserCreateSchema) -> UserOutSchema:
        """
        Crée un nouvel utilisateur avec validation et gestion transactionnelle.

        :param user_data: Schéma contenant les informations nécessaires à la création
        :return: Instance du User créé
        """
        try:
            # Validation des données métier
            await self._validate_user_data(user_data)
            
            # Hash du mot de passe
            hashed_password = self._hash_password(user_data.password)
            
            # Création transactionnelle
            async with in_transaction():
                user = await User.create(
                    email=user_data.email,
                    phone=user_data.phone,
                    password_hash=hashed_password,
                    first_name=user_data.first_name,
                    last_name=user_data.last_name,
                    user_type= user_data.user_type if user_data.user_type and user_data.user_type != UserType.ADMIN else UserType.CUSTOMER,
                    avatar_url=user_data.avatar_url
                )
                
                logger.info(f"Utilisateur créé avec succès: {user.id}", 
                          extra={"user_id": str(user.id), "email": user.email})
                
                return UserOutSchema.from_orm(user)
                
        except IntegrityError as e:
            logger.error(f"Erreur d'intégrité lors de la création utilisateur: {str(e)}")
            if "email" in str(e).lower():
                raise ConflictException(detail="Cet email est déjà utilisé")
            elif "phone" in str(e).lower():
                raise ConflictException(detail="Ce numéro de téléphone est déjà utilisé")
            else:
                raise ConflictException(detail="Données utilisateur invalides ou conflit")
                
        except ValidationError as e:
            logger.error(f"Erreur de validation des données: {str(e)}")
            raise APIException(detail=f"Données utilisateur invalides: {str(e)}")

        except HTTPException as e:
            # On loggue, mais on relaisse passer l'exception à FastAPI
            logger.warning(f"Exception HTTP: {e.detail}")
            raise e  # 🔥 Important : ne pas la remplacer !
            
        except Exception as e:
            logger.error(f"Erreur inattendue lors de la création utilisateur: {str(e)}")
            raise InternalServerException(detail="Erreur lors de la création de l'utilisateur")

    async def get_user(self, user_id: str) -> UserOutSchema:
        """
        Récupère un utilisateur par son ID avec validation UUID.

        :param user_id: UUID de l'utilisateur
        :return: Instance du User
        """
        try:
            # Validation UUID
            try:
                uuid.UUID(user_id)
            except ValueError:
                raise APIException(detail="Format d'ID utilisateur invalide")
            
            user = await User.get(id=user_id)
            return UserOutSchema.from_orm(user)
            
        except DoesNotExist:
            logger.warning(f"Utilisateur non trouvé: {user_id}")
            raise NotFoundException(detail=f"Utilisateur avec ID {user_id} introuvable")
    
        except HTTPException as e:
            # On loggue, mais on relaisse passer l'exception à FastAPI
            logger.warning(f"Exception HTTP: {e.detail}")
            raise e  # 🔥 Important : ne pas la remplacer !
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération de l'utilisateur {user_id}: {str(e)}")
            raise InternalServerException(detail="Erreur lors de la récupération de l'utilisateur")

    async def get_all_users(self, limit: int = 100, offset: int = 0, 
                          is_active: Optional[bool] = None,
                          user_type: Optional[UserType] = None) -> List[UserOutSchema]:
        """
        Récupère tous les utilisateurs avec pagination et filtres avancés.

        :param limit: Nombre maximal d'utilisateurs à retourner (max 1000)
        :param offset: Décalage pour la pagination
        :param is_active: Filtre par statut actif/inactif
        :param user_type: Filtre par type d'utilisateur
        :return: Liste d'utilisateurs
        """
        try:
            # Validation des paramètres
            if limit > 1000:
                raise APIException(detail="La limite ne peut pas dépasser 1000")
            if limit < 1:
                raise APIException(detail="La limite doit être positive")
            if offset < 0:
                raise APIException(detail="L'offset ne peut pas être négatif")
            
            query = User.all()
            
            # Application des filtres
            if is_active is not None:
                query = query.filter(is_active=is_active)
            if user_type is not None:
                query = query.filter(user_type=user_type)
            
            users = await query.offset(offset).limit(limit)
            return [UserOutSchema.from_orm(user) for user in users]
            
        except HTTPException as e:
            # On loggue, mais on relaisse passer l'exception à FastAPI
            logger.warning(f"Exception HTTP: {e.detail}")
            raise e  # 🔥 Important : ne pas la remplacer !
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des utilisateurs: {str(e)}")
            raise InternalServerException(detail="Erreur lors de la récupération des utilisateurs")

    async def update_user(self, user_id: str, user_data: UserUpdateSchema) -> UserOutSchema:
        """
        Met à jour complètement ou partiellement un utilisateur.

        :param user_id: UUID de l'utilisateur à mettre à jour
        :param user_data: Schéma contenant les informations à mettre à jour
        :return: Instance du User mise à jour
        """
        try:
            # Récupération de l'utilisateur
            user = await User.get(id=user_id)
            
            # Validation des données uniques si fournies
            if user_data.email and user_data.email != user.email:
                if await User.filter(email=user_data.email).exclude(id=user_id).exists():
                    raise ConflictException(detail="Cet email est déjà utilisé")
            
            if user_data.phone and user_data.phone != user.phone:
                if await User.filter(phone=user_data.phone).exclude(id=user_id).exists():
                    raise ConflictException(detail="Ce numéro de téléphone est déjà utilisé")
            
            # Mise à jour transactionnelle
            async with in_transaction():
                update_data = user_data.dict(exclude_unset=True)
                
                # Gestion spécifique du mot de passe
                if 'password' in update_data and update_data['password']:
                    #update_data['password_hash'] = self._hash_password(update_data.pop('password'))
                    #la miise à jour des mots de passe arrivera apres
                    pass
                
                
                
                for field, value in update_data.items():
                    
                    if hasattr(user, field):
                        setattr(user,field, value)
                
                await user.save()
                
                logger.info(f"Utilisateur mis à jour: {user_id}")
                return UserOutSchema.from_orm(user)
                
        except DoesNotExist:
            raise NotFoundException(detail=f"Utilisateur avec ID {user_id} introuvable")
            
        except IntegrityError as e:
            logger.error(f"Erreur d'intégrité lors de la mise à jour: {str(e)}")
            raise ConflictException(detail="Conflit de données lors de la mise à jour")

        except HTTPException as e:
            # On loggue, mais on relaisse passer l'exception à FastAPI
            logger.warning(f"Exception HTTP: {e.detail}")
            raise e  # 🔥 Important : ne pas la remplacer !
            
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour de l'utilisateur {user_id}: {str(e)}")
            raise InternalServerException(detail="Erreur lors de la mise à jour de l'utilisateur")

    async def delete_user(self, user_id: str) -> DeleteResponseSchema:
        """
        Supprime un utilisateur de manière sécurisée.

        :param user_id: UUID de l'utilisateur à supprimer
        :return: True si suppression réussie
        """
        try:
            user = await User.get(id=user_id)
            
            # Logique métier : vérifications avant suppression
            # Par exemple, vérifier qu'il n'a pas de commandes en cours, etc.
            
            async with in_transaction():
                await user.delete()
                
            logger.info(f"Utilisateur supprimé: {user_id}")
            return DeleteResponseSchema()
            
        except DoesNotExist:
            raise NotFoundException(detail=f"Utilisateur avec ID {user_id} introuvable")
        
        except HTTPException as e:
            # On loggue, mais on relaisse passer l'exception à FastAPI
            logger.warning(f"Exception HTTP: {e.detail}")
            raise e  # 🔥 Important : ne pas la remplacer !
            
        except Exception as e:
            logger.error(f"Erreur lors de la suppression de l'utilisateur {user_id}: {str(e)}")
            raise InternalServerException(detail="Erreur lors de la suppression de l'utilisateur")

    async def deactivate_user(self, user_id: str) -> UserOutSchema:
        """
        Désactive un utilisateur (soft delete).

        :param user_id: UUID de l'utilisateur à désactiver
        :return: Instance du User désactivé
        """
        try:
            user = await User.get(id=user_id)
            
            if not user.is_active:
                raise APIException(detail="L'utilisateur est déjà désactivé")
            
            async with in_transaction():
                user.is_active = False
                await user.save()
                
            logger.info(f"Utilisateur désactivé: {user_id}")
            return UserOutSchema.from_orm(user)
            
        except DoesNotExist:
            raise NotFoundException(detail=f"Utilisateur avec ID {user_id} introuvable")
            
        except Exception as e:
            logger.error(f"Erreur lors de la désactivation de l'utilisateur {user_id}: {str(e)}")
            raise InternalServerException(detail="Erreur lors de la désactivation de l'utilisateur")

    async def activate_user(self, user_id: str) -> UserOutSchema:
        """
        Active un utilisateur précédemment désactivé.

        :param user_id: UUID de l'utilisateur à activer
        :return: Instance du User activé
        """
        try:
            user = await User.get(id=user_id)
            
            if user.is_active:
                raise APIException(detail="L'utilisateur est déjà activé")
            
            async with in_transaction():
                user.is_active = True
                await user.save()
                
            logger.info(f"Utilisateur activé: {user_id}")
            return UserOutSchema.from_orm(user)
            
        except DoesNotExist:
            raise NotFoundException(detail=f"Utilisateur avec ID {user_id} introuvable")
        
        except HTTPException as e:
            # On loggue, mais on relaisse passer l'exception à FastAPI
            logger.warning(f"Exception HTTP: {e.detail}")
            raise e  # 🔥 Important : ne pas la remplacer !
            
        except Exception as e:
            logger.error(f"Erreur lors de l'activation de l'utilisateur {user_id}: {str(e)}")
            raise InternalServerException(detail="Erreur lors de l'activation de l'utilisateur")

    async def update_user_status(self, user_id: str, status_data: UserStatusUpdateSchema) -> UserOutSchema:
        """
        Met à jour le statut d'un utilisateur (actif/inactif).

        :param user_id: UUID de l'utilisateur
        :param status_data: Données de statut
        :return: Instance du User mise à jour
        """
        try:
            user = await User.get(id=user_id)
            
            async with in_transaction():
                user.is_active = status_data.is_active
                await user.save()
                
            action = "activé" if status_data.is_active else "désactivé"
            logger.info(f"Statut utilisateur mis à jour: {user_id} -> {action}")
            return UserOutSchema.from_orm(user)
            
        except DoesNotExist:
            raise NotFoundException(detail=f"Utilisateur avec ID {user_id} introuvable")
        
        except HTTPException as e:
            # On loggue, mais on relaisse passer l'exception à FastAPI
            logger.warning(f"Exception HTTP: {e.detail}")
            raise e  # 🔥 Important : ne pas la remplacer !
            
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour du statut {user_id}: {str(e)}")
            raise InternalServerException(detail="Erreur lors de la mise à jour du statut")

    async def verify_user(self, user_id: str) -> UserOutSchema:
        """
        Marque un utilisateur comme vérifié.

        :param user_id: UUID de l'utilisateur
        :return: Instance du User vérifié
        """
        try:
            user = await User.get(id=user_id)
            
            if user.is_verified:
                raise APIException(detail="L'utilisateur est déjà vérifié")
            
            async with in_transaction():
                user.is_verified = True
                await user.save()
                
            logger.info(f"Utilisateur vérifié: {user_id}")
            return UserOutSchema.from_orm(user)
            
        except DoesNotExist:
            raise NotFoundException(detail=f"Utilisateur avec ID {user_id} introuvable")
        
        except HTTPException as e:
            # On loggue, mais on relaisse passer l'exception à FastAPI
            logger.warning(f"Exception HTTP: {e.detail}")
            raise e  # 🔥 Important : ne pas la remplacer !
            
        except Exception as e:
            logger.error(f"Erreur lors de la vérification de l'utilisateur {user_id}: {str(e)}")
            raise InternalServerException(detail="Erreur lors de la vérification de l'utilisateur")

    async def update_user_rating(self, user_id: str, new_rating: float) -> UserOutSchema:
        """
        Met à jour la note d'un utilisateur.

        :param user_id: UUID de l'utilisateur
        :param new_rating: Nouvelle note à ajouter
        :return: Instance du User mise à jour
        """
        try:
            if not (0 <= new_rating <= 5):
                raise APIException(detail="La note doit être entre 0 et 5")
            
            user = await User.get(id=user_id)
            
            async with in_transaction():
                # Calcul de la nouvelle moyenne
                total_score = (user.rating * user.total_ratings) + new_rating
                user.total_ratings += 1
                user.rating = total_score / user.total_ratings
                await user.save()
                
            logger.info(f"Note utilisateur mise à jour: {user_id} -> {user.rating:.2f}")
            return UserOutSchema.from_orm(user)
            
        except DoesNotExist:
            raise NotFoundException(detail=f"Utilisateur avec ID {user_id} introuvable")
        
        except HTTPException as e:
            # On loggue, mais on relaisse passer l'exception à FastAPI
            logger.warning(f"Exception HTTP: {e.detail}")
            raise e  # 🔥 Important : ne pas la remplacer !
            
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour de la note {user_id}: {str(e)}")
            raise InternalServerException(detail="Erreur lors de la mise à jour de la note")

    async def user_exists(self, user_id: str) -> UserExistsResponseSchema:
        """
        Vérifie si un utilisateur existe.

        :param user_id: UUID de l'utilisateur
        :return: True si l'utilisateur existe
        """
        try:
            return UserExistsResponseSchema(exists=await User.filter(id=user_id).exists())
        except Exception as e:
            logger.error(f"Erreur lors de la vérification d'existence {user_id}: {str(e)}")
            return False

    async def get_users_count(self, is_active: Optional[bool] = None) -> UserCountResponseSchema:
        """
        Retourne le nombre total d'utilisateurs avec filtres optionnels.

        :param is_active: Filtre par statut actif/inactif
        :return: Nombre d'utilisateurs
        """
        try:
            query = User.all()
            if is_active is not None:
                query = query.filter(is_active=is_active)
            return UserCountResponseSchema(count=await query.count())
        except Exception as e:
            logger.error(f"Erreur lors du comptage des utilisateurs: {str(e)}")
            raise InternalServerException(detail="Erreur lors du comptage des utilisateurs")

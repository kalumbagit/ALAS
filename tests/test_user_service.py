# tests/test_user_service.py
import sys
import os
import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, date, timedelta
from uuid import uuid4
from tortoise.exceptions import DoesNotExist, IntegrityError, ValidationError

# Configuration du path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models.user_model import User
from app.schemas.user_schema import (
    UserCreateSchema, 
    UserUpdateSchema, 
    UserOutSchema, 
    UserStatusUpdateSchema
)
from app.core.enums import UserType
from app.core.exceptions import (
    APIException, 
    NotFoundException, 
    ConflictException, 
    InternalServerException
)
from app.services.user_service import UserService


class AwaitableRaises:
    def __init__(self, exc):
        self.exc = exc

    def __await__(self):
        raise self.exc
        yield  # pour respecter le protocole awaitable


class TestUserService:
    """Tests complets et professionnels pour UserService"""

    @pytest.fixture
    def user_service(self):
        """Fixture pour créer une instance de UserService"""
        return UserService()

    @pytest.fixture
    def sample_user_data(self):
        """Fixture pour des données utilisateur valides"""
        return UserCreateSchema(
            email="test@example.com",
            phone="+1234567890",
            password="securepassword123",
            first_name="John",
            last_name="Doe",
            user_type = UserType.CUSTOMER,
            avatar_url="https://example.com/avatar.jpg",
            date_of_birth=date(1990, 1, 1)
        )

    @pytest.fixture
    def sample_user_update_data(self):
        """Fixture pour des données de mise à jour utilisateur"""
        return UserUpdateSchema(
            first_name="Jane",
            last_name="Smith",
            email="updated@example.com",
            phone="+0987654321"
        )

    @pytest.fixture
    def sample_user_status_data(self):
        """Fixture pour des données de statut utilisateur"""
        return UserStatusUpdateSchema(is_active=False)

    @pytest.fixture
    def mock_user(self):
        """Fixture pour un utilisateur mocké"""
        user_id = uuid4()
        user = MagicMock(spec=User)
        user.id = user_id
        user.email = "test@example.com"
        user.phone = "+1234567890"
        user.password_hash = "hashed_password"
        user.first_name = "John"
        user.last_name = "Doe"
        user.user_type = UserType.CUSTOMER  # Utiliser .value pour l'enum
        user.avatar_url = "https://example.com/avatar.jpg"
        user.date_of_birth = date(1990, 1, 1)
        user.is_verified = False
        user.is_active = True
        user.rating = 0.0
        user.total_ratings = 0
        user.created_at = datetime.now()
        user.updated_at = datetime.now()
        user.save = AsyncMock()
        user.delete = AsyncMock()
        return user

    def create_user_out_schema(self, user_data, user_id=None):
        """Helper pour créer un UserOutSchema valide"""
        return UserOutSchema(
            id=str(user_id) if user_id else str(uuid4()),
            email=user_data.get('email', 'test@example.com'),
            phone=user_data.get('phone', '+1234567890'),
            first_name=user_data.get('first_name', 'John'),
            last_name=user_data.get('last_name', 'Doe'),
            user_type=UserType.CUSTOMER,  # Utiliser l'enum directement, pas .value
            avatar_url=user_data.get('avatar_url', 'https://example.com/avatar.jpg'),
            rating=user_data.get('rating', 0.0),
            total_ratings=user_data.get('total_ratings', 0)
        )

    @pytest.mark.asyncio
    async def test_create_user_success(self, user_service, sample_user_data,mock_user):
        """Test la création réussie d'un utilisateur"""
        with patch("app.services.user_service.UserService._validate_user_data") as mock_validate, \
             patch("app.services.user_service.User.create", new_callable=AsyncMock) as mock_create, \
             patch('app.services.user_service.logger') as mock_logger:
            
            # Configuration des mocks
            mock_validate.return_value = None
            mock_create.return_value = mock_user
            
            # Mock pour UserOutSchema.from_orm
            with patch("app.services.user_service.UserOutSchema.from_orm") as mock_from_orm:
                mock_from_orm.return_value = self.create_user_out_schema(
                    {'email': sample_user_data.email},
                    mock_user.id
                )
                
                # Appel de la méthode
                result = await user_service.create_user(sample_user_data)
                
                # Vérifications
                mock_validate.assert_called_once_with(sample_user_data)
                mock_create.assert_awaited_once()  # ✅ car User.create est async
                mock_logger.info.assert_called_once()
                assert isinstance(result, UserOutSchema)

    @pytest.mark.asyncio
    async def test_create_user_email_conflict(self, user_service, sample_user_data):
        """Test la création d'un utilisateur avec email existant"""
        with patch("app.services.user_service.UserService._validate_user_data") as mock_validate:
            mock_validate.side_effect = ConflictException("L'email est déjà utilisé")
            
            # Vérification que l'exception est levée
            with pytest.raises(ConflictException):
                await user_service.create_user(sample_user_data)

    @pytest.mark.asyncio
    async def test_create_user_integrity_error(self, user_service, sample_user_data):
        """Test la gestion des erreurs d'intégrité"""
        with patch("app.services.user_service.UserService._validate_user_data") as mock_validate, \
             patch("app.services.user_service.User.create", new_callable=AsyncMock) as mock_create:
            
            mock_validate.return_value = None
            mock_create.side_effect = IntegrityError("email unique constraint")
            
            with pytest.raises(ConflictException):
                await user_service.create_user(sample_user_data)

    @pytest.mark.asyncio
    async def test_create_user_validation_error(self, user_service, sample_user_data):
        """Test la gestion des erreurs de validation"""
        with patch("app.services.user_service.UserService._validate_user_data") as mock_validate:
            mock_validate.side_effect = ValidationError("Invalid data")
            
            with pytest.raises(APIException):
                await user_service.create_user(sample_user_data)

    @pytest.mark.asyncio
    async def test_create_user_underage(self, user_service):
        """Test la création d'un utilisateur mineur"""
        with patch("app.services.user_service.UserService._validate_user_data") as mock_validate:
            mock_validate.side_effect = APIException("L'utilisateur doit avoir au moins 18 ans")
            
            underage_data = UserCreateSchema(
                email="underage@example.com",
                phone="+1234567891",
                password="password123",
                first_name="Minor",
                last_name="User",
                avatar_url=None,
                date_of_birth=date.today() - timedelta(days=365*17)  # 17 ans
            )
            
            with pytest.raises(APIException) as exc_info:
                await user_service.create_user(underage_data)
            
            assert "18 ans" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_get_user_success(self, user_service, mock_user):
        """Test la récupération réussie d'un utilisateur"""
        user_id = str(mock_user.id)
        
        with patch("app.services.user_service.User.get", new_callable=AsyncMock) as mock_get, \
             patch("app.services.user_service.UserOutSchema.from_orm") as mock_from_orm:
            
            mock_get.return_value = mock_user
            mock_from_orm.return_value = self.create_user_out_schema(
                {'email': mock_user.email},
                mock_user.id
            )
            
            result = await user_service.get_user(user_id)
            
            mock_get.assert_called_once_with(id=user_id)
            assert isinstance(result, UserOutSchema)
            assert result.email == mock_user.email

    @pytest.mark.asyncio
    async def test_get_user_not_found(self, user_service):
        """Test la récupération d'un utilisateur inexistant"""
        user_id = str(uuid4())
        
        with patch("app.services.user_service.User.get", new_callable=AsyncMock) as mock_get:
            # Correction: DoesNotExist doit être levé comme exception
            mock_get.side_effect = DoesNotExist("User not found")
            
            with pytest.raises(NotFoundException):
                await user_service.get_user(user_id)

    @pytest.mark.asyncio
    async def test_get_user_invalid_uuid(self, user_service):
        """Test la récupération avec un UUID invalide"""
        invalid_uuid = "invalid-uuid"
        
        with pytest.raises(APIException) as exc_info:
            await user_service.get_user(invalid_uuid)
        
        assert "Format d'ID" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_get_all_users_success(self, user_service, mock_user):
        """Test la récupération de tous les utilisateurs"""
        mock_users = [mock_user]
        
        with patch("app.services.user_service.User.all") as mock_all, \
             patch("app.services.user_service.UserOutSchema.from_orm") as mock_from_orm:
            
            mock_query = AsyncMock()
            mock_query.offset.return_value = mock_query
            mock_query.limit.return_value = mock_query
            mock_query.filter.return_value = mock_query
            mock_query.__aiter__.return_value = iter(mock_users)
            mock_all.return_value = mock_query
            
            mock_from_orm.return_value = self.create_user_out_schema(
                {'email': mock_user.email},
                mock_user.id
            )
            
            result = await user_service.get_all_users(limit=10, offset=0)
            
            assert len(result) == 1
            assert all(isinstance(user, UserOutSchema) for user in result)

    @pytest.mark.asyncio
    async def test_get_all_users_with_filters(self, user_service, mock_user):
        """Test la récupération avec filtres"""
        mock_users = [mock_user]
        
        with patch("app.services.user_service.User.all") as mock_all, \
             patch("app.services.user_service.UserOutSchema.from_orm") as mock_from_orm:
            
            mock_query = AsyncMock()
            mock_query.offset.return_value = mock_query
            mock_query.limit.return_value = mock_query
            mock_query.filter.return_value = mock_query
            mock_query.__aiter__.return_value = iter(mock_users)
            mock_all.return_value = mock_query
            
            mock_from_orm.return_value = self.create_user_out_schema(
                {'email': mock_user.email},
                mock_user.id
            )
            
            result = await user_service.get_all_users(
                limit=10, 
                offset=0, 
                is_active=True, 
                user_type=UserType.CUSTOMER
            )
            
            assert len(result) == 1
            # Vérifier que filter a été appelé
            assert mock_query.filter.called

    @pytest.mark.asyncio
    async def test_get_all_users_invalid_limit(self, user_service):
        """Test avec une limite invalide"""
        with pytest.raises(APIException):
            await user_service.get_all_users(limit=0)
        
        with pytest.raises(APIException):
            await user_service.get_all_users(limit=1001)

    @pytest.mark.asyncio
    async def test_get_all_users_invalid_offset(self, user_service):
        """Test avec un offset invalide"""
        with pytest.raises(APIException):
            await user_service.get_all_users(offset=-1)

    @pytest.mark.asyncio
    async def test_update_user_success(self, user_service, mock_user, sample_user_update_data):
        """Test la mise à jour réussie d'un utilisateur"""
        user_id = str(mock_user.id)
        
        with patch("app.services.user_service.User.get", new_callable=AsyncMock) as mock_get, \
             patch("app.services.user_service.User.filter") as mock_filter, \
             patch("app.services.user_service.UserOutSchema.from_orm") as mock_from_orm:
            
            mock_get.return_value = mock_user
            mock_filter.return_value.exists.return_value = False
            mock_from_orm.return_value = self.create_user_out_schema(
                {
                    'email': sample_user_update_data.email or mock_user.email,
                    'first_name': sample_user_update_data.first_name or mock_user.first_name,
                    'last_name': sample_user_update_data.last_name or mock_user.last_name
                },
                mock_user.id
            )
            
            result = await user_service.update_user(user_id, sample_user_update_data)
            
            mock_get.assert_called_once_with(id=user_id)
            mock_user.save.assert_awaited_once()
            assert isinstance(result, UserOutSchema)

    @pytest.mark.asyncio
    async def test_update_user_email_conflict(self, user_service, mock_user, sample_user_update_data):
        """Test la mise à jour avec email existant"""
        user_id = str(mock_user.id)
        
        with patch("app.services.user_service.User.get", new_callable=AsyncMock) as mock_get, \
             patch("app.services.user_service.User.filter") as mock_filter:
            
            mock_get.return_value = mock_user
            mock_filter.return_value.exists.return_value = True  # Email existe déjà
            
            with pytest.raises(ConflictException):
                await user_service.update_user(user_id, sample_user_update_data)

    @pytest.mark.asyncio
    async def test_update_user_not_found(self, user_service, sample_user_update_data):
        """Test la mise à jour d'un utilisateur inexistant"""
        user_id = str(uuid4())

        # ✅ Crée une coroutine side effect qui simule l'exception async
        async def fake_get(**kwargs):
            raise DoesNotExist("User not found")

        # ✅ Patch proprement la méthode asynchrone
        with patch("app.services.user_service.User.get", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = fake_get  # ⚡️ Le side_effect est une coroutine ici

            # ✅ On attend bien que le service gère l'exception
            with pytest.raises(NotFoundException) as exc_info:
                await user_service.update_user(user_id, sample_user_update_data)

            # ✅ Vérifie que la fonction a bien été appelée avec l’ID correct
            mock_get.assert_awaited_once_with(id=user_id)

            # ✅ Optionnel : vérifie le message d'erreur si besoin
            assert "introuvable" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_delete_user_success(self, user_service, mock_user):
        """Test la suppression réussie d'un utilisateur"""
        user_id = str(mock_user.id)
        
        with patch("app.services.user_service.User.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_user
            
            result = await user_service.delete_user(user_id)
            
            mock_get.assert_called_once_with(id=user_id)
            mock_user.delete.assert_awaited_once()
            assert result is True

    @pytest.mark.asyncio
    async def test_delete_user_not_found(self, user_service):
        """Test la suppression d'un utilisateur inexistant"""
        user_id = str(uuid4())
        
        with patch("app.services.user_service.User.get", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = DoesNotExist("User not found")
            
            with pytest.raises(NotFoundException):
                await user_service.delete_user(user_id)

    @pytest.mark.asyncio
    async def test_deactivate_user_success(self, user_service, mock_user):
        """Test la désactivation réussie d'un utilisateur"""
        user_id = str(mock_user.id)
        mock_user.is_active = True
        
        with patch("app.services.user_service.User.get", new_callable=AsyncMock) as mock_get, \
             patch("app.services.user_service.UserOutSchema.from_orm") as mock_from_orm:
            
            mock_get.return_value = mock_user
            mock_from_orm.return_value = self.create_user_out_schema(
                {'is_active': False},
                mock_user.id
            )
            
            result = await user_service.deactivate_user(user_id)
            
            mock_user.save.assert_awaited_once()
            assert isinstance(result, UserOutSchema)

    @pytest.mark.asyncio
    async def test_deactivate_user_already_inactive(self, user_service, mock_user):
        """Test la désactivation d'un utilisateur déjà inactif"""
        user_id = str(mock_user.id)
        mock_user.is_active = False
        
        with patch("app.services.user_service.User.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_user
            
            with pytest.raises(APIException) as exc_info:
                await user_service.deactivate_user(user_id)
            
            assert "déjà désactivé" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_activate_user_success(self, user_service, mock_user):
        """Test l'activation réussie d'un utilisateur"""
        user_id = str(mock_user.id)
        mock_user.is_active = False
        
        with patch("app.services.user_service.User.get", new_callable=AsyncMock) as mock_get, \
             patch("app.services.user_service.UserOutSchema.from_orm") as mock_from_orm:
            
            mock_get.return_value = mock_user
            mock_from_orm.return_value = self.create_user_out_schema(
                {'is_active': True},
                mock_user.id
            )
            
            result = await user_service.activate_user(user_id)
            
            mock_user.save.assert_awaited_once()
            assert isinstance(result, UserOutSchema)

    @pytest.mark.asyncio
    async def test_activate_user_already_active(self, user_service, mock_user):
        """Test l'activation d'un utilisateur déjà actif"""
        user_id = str(mock_user.id)
        mock_user.is_active = True
        
        with patch("app.services.user_service.User.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_user
            
            with pytest.raises(APIException) as exc_info:
                await user_service.activate_user(user_id)
            
            assert "déjà activé" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_update_user_status_success(self, user_service, mock_user, sample_user_status_data):
        """Test la mise à jour du statut utilisateur"""
        user_id = str(mock_user.id)
        
        with patch("app.services.user_service.User.get", new_callable=AsyncMock) as mock_get, \
             patch("app.services.user_service.UserOutSchema.from_orm") as mock_from_orm:
            
            mock_get.return_value = mock_user
            mock_from_orm.return_value = self.create_user_out_schema(
                {'is_active': sample_user_status_data.is_active},
                mock_user.id
            )
            
            result = await user_service.update_user_status(user_id, sample_user_status_data)
            
            mock_user.save.assert_awaited_once()
            assert isinstance(result, UserOutSchema)

    @pytest.mark.asyncio
    async def test_verify_user_success(self, user_service, mock_user):
        """Test la vérification réussie d'un utilisateur"""
        user_id = str(mock_user.id)
        mock_user.is_verified = False
        
        with patch("app.services.user_service.User.get", new_callable=AsyncMock) as mock_get, \
             patch("app.services.user_service.UserOutSchema.from_orm") as mock_from_orm:
            
            mock_get.return_value = mock_user
            mock_from_orm.return_value = self.create_user_out_schema(
                {'is_verified': True},
                mock_user.id
            )
            
            result = await user_service.verify_user(user_id)
            
            mock_user.save.assert_awaited_once()
            assert isinstance(result, UserOutSchema)

    @pytest.mark.asyncio
    async def test_verify_user_already_verified(self, user_service, mock_user):
        """Test la vérification d'un utilisateur déjà vérifié"""
        user_id = str(mock_user.id)
        mock_user.is_verified = True
        
        with patch("app.services.user_service.User.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_user
            
            with pytest.raises(APIException) as exc_info:
                await user_service.verify_user(user_id)
            
            assert "déjà vérifié" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_update_user_rating_success(self, user_service, mock_user):
        """Test la mise à jour de la note utilisateur"""
        user_id = str(mock_user.id)
        mock_user.rating = 4.0
        mock_user.total_ratings = 1
        
        with patch("app.services.user_service.User.get", new_callable=AsyncMock) as mock_get, \
             patch("app.services.user_service.UserOutSchema.from_orm") as mock_from_orm:
            
            mock_get.return_value = mock_user
            mock_from_orm.return_value = self.create_user_out_schema(
                {'rating': 4.5, 'total_ratings': 2},
                mock_user.id
            )
            
            result = await user_service.update_user_rating(user_id, 5.0)
            
            mock_user.save.assert_awaited_once()
            assert isinstance(result, UserOutSchema)

    @pytest.mark.asyncio
    async def test_update_user_rating_invalid(self, user_service):
        """Test la mise à jour avec une note invalide"""
        user_id = str(uuid4())
        
        # Note trop basse
        with pytest.raises(APIException):
            await user_service.update_user_rating(user_id, -1.0)
        
        # Note trop haute
        with pytest.raises(APIException):
            await user_service.update_user_rating(user_id, 6.0)

    @pytest.mark.asyncio
    async def test_user_exists_success(self, user_service):
        """Test la vérification d'existence d'un utilisateur"""
        user_id = str(uuid4())
        
        with patch("app.services.user_service.User.filter") as mock_filter:
            mock_query = AsyncMock()
            mock_query.exists.return_value = True
            mock_filter.return_value = mock_query
            
            result = await user_service.user_exists(user_id)
            
            mock_filter.assert_called_once_with(id=user_id)
            mock_query.exists.assert_awaited_once()
            assert result is True

    @pytest.mark.asyncio
    async def test_get_users_count_success(self, user_service):
        """Test le comptage des utilisateurs"""
        expected_count = 5
        
        with patch("app.services.user_service.User.all", new_callable=AsyncMock) as mock_all:
            mock_query = AsyncMock()
            mock_query.filter.return_value = mock_query
            mock_query.count.return_value = expected_count
            mock_all.return_value = mock_query
            
            result = await user_service.get_users_count(is_active=True)
            
            assert result == expected_count

    def test_hash_password(self, user_service):
        """Test le hashage des mots de passe"""
        password = "test"  # Mot de passe très court pour éviter l'erreur bcrypt
        
        hashed = user_service._hash_password(password)
        
        assert hashed != password
        assert isinstance(hashed, str)
        assert len(hashed) > 0

    @pytest.mark.asyncio
    async def test_validate_user_data_success(self, user_service, sample_user_data):
        """Test la validation réussie des données utilisateur"""
        with patch("app.services.user_service.User.filter") as mock_filter:
            mock_query = AsyncMock()
            mock_query.exists.return_value = False
            mock_filter.return_value = mock_query
            
            # Ne doit pas lever d'exception
            await user_service._validate_user_data(sample_user_data)

    @pytest.mark.asyncio
    async def test_validate_user_data_email_exists(self, user_service, sample_user_data):
        """Test la validation avec email existant"""
        with patch("app.services.user_service.User.filter") as mock_filter:
            mock_query = AsyncMock()
            # Premier appel pour email -> True (existe)
            # Deuxième appel pour phone -> False (n'existe pas)
            mock_query.exists.side_effect = [True, False]
            mock_filter.return_value = mock_query
            
            with pytest.raises(ConflictException) as exc_info:
                await user_service._validate_user_data(sample_user_data)
            
            assert "email" in str(exc_info.value.detail).lower()

    @pytest.mark.asyncio
    async def test_validate_user_data_phone_exists(self, user_service, sample_user_data):
        """Test la validation avec téléphone existant"""
        with patch("app.services.user_service.User.filter") as mock_filter:
            mock_query = AsyncMock()
            # Premier appel pour email -> False (n'existe pas)
            # Deuxième appel pour phone -> True (existe)
            mock_query.exists.side_effect = [False, True]
            mock_filter.return_value = mock_query
            
            with pytest.raises(ConflictException) as exc_info:
                await user_service._validate_user_data(sample_user_data)
            
            assert "téléphone" in str(exc_info.value.detail).lower()


# Configuration pour éviter les warnings pytest-asyncio
@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()
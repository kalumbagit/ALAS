# app/core/exceptions.py

from fastapi import HTTPException, status
from typing import Any, Dict


class APIException(HTTPException):
    """
    Classe personnalisée pour gérer les exceptions API de manière standardisée.
    """

    def __init__(self, 
                 status_code: int = status.HTTP_400_BAD_REQUEST,
                 detail: str = "Une erreur est survenue",
                 headers: Dict[str, Any] = None):
        """
        :param status_code: code HTTP de l'erreur
        :param detail: message d'erreur
        :param headers: headers supplémentaires (optionnel)
        """
        super().__init__(status_code=status_code, detail=detail, headers=headers)


class NotFoundException(APIException):
    def __init__(self, detail: str = "Ressource non trouvée"):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


class UnauthorizedException(APIException):
    def __init__(self, detail: str = "Non autorisé"):
        super().__init__(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)


class ForbiddenException(APIException):
    def __init__(self, detail: str = "Accès interdit"):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


class ConflictException(APIException):
    def __init__(self, detail: str = "Conflit avec l'état actuel de la ressource"):
        super().__init__(status_code=status.HTTP_409_CONFLICT, detail=detail)


class InternalServerException(APIException):
    def __init__(self, detail: str = "Erreur interne du serveur"):
        super().__init__(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=detail)

#-----------------------------------------------------------------
# Exceptions spécifiques aux livreurs
#-----------------------------------------------------------------
class DelivererException(HTTPException):
    """Exception de base pour les livreurs"""
    def __init__(self, detail: str, status_code: int = status.HTTP_400_BAD_REQUEST):
        super().__init__(status_code=status_code, detail=detail)

class DelivererNotFoundException(DelivererException):
    def __init__(self, deliverer_id: str):
        detail = f"Livreur avec ID {deliverer_id} introuvable"
        super().__init__(detail=detail, status_code=status.HTTP_404_NOT_FOUND)

class DelivererAlreadyExistsException(DelivererException):
    def __init__(self, user_id: str):
        detail = f"L'utilisateur {user_id} est déjà un livreur"
        super().__init__(detail=detail)

class InvalidReferralCodeException(DelivererException):
    def __init__(self, referral_code: str):
        detail = f"Code de parrainage invalide: {referral_code}"
        super().__init__(detail=detail)

class DelivererSuspendedException(DelivererException):
    def __init__(self, deliverer_id: str):
        detail = f"Livreur {deliverer_id} est suspendu"
        super().__init__(detail=detail)

class DelivererNotActiveException(DelivererException):
    def __init__(self, deliverer_id: str):
        detail = f"Livreur {deliverer_id} n'est pas actif"
        super().__init__(detail=detail)


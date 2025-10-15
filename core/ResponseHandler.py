from typing import Any, Dict, Optional, List
from fastapi.responses import JSONResponse as FAPIResponse
from fastapi import Response
from pydantic import BaseModel

from starlette.status import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_204_NO_CONTENT,
    HTTP_400_BAD_REQUEST,
    HTTP_401_UNAUTHORIZED,
    HTTP_403_FORBIDDEN,
    HTTP_404_NOT_FOUND,
    HTTP_500_INTERNAL_SERVER_ERROR,
    HTTP_409_CONFLICT,
    HTTP_501_NOT_IMPLEMENTED,
)
from core.enums import ResponseStatus


class APIResponse:
    """
    Factory for standardized API responses across the agency service.
    
    Patterns:
    - Success: {status, message, data, metadata}
    - Error: {status, code, message, errors}
    """
    @staticmethod
    def _serialize_data(data: Any):
        """Convertit automatiquement les modèles Pydantic ou ORM en dict."""
        if isinstance(data, BaseModel):
            return data.model_dump()
        elif isinstance(data, list):
            return [APIResponse._serialize_data(item) for item in data]
        return data

    @staticmethod
    def success(
        data: Any = None,
        message: str = None,
        metadata: Optional[Dict] = None,
        status_code: int = HTTP_200_OK,
        headers: Optional[Dict] = None
    ) -> FAPIResponse:
        """
        Standard success response.
        
        Args:
            data: Main response payload
            message: Human-readable message
            metadata: Additional pagination/context data
            status_code: Appropriate 2xx status code
            headers: Custom HTTP headers
            
        Example:
            APIResponse.success(
                data={'id': 1},
                message='Resource created',
                status_code=status.HTTP_201_CREATED
            )
        """
        return FAPIResponse(
            {
                'status': ResponseStatus.SUCCESS.value,
                'message': message,
                'data': data,
                'metadata': metadata or {}
            },
            status_code=status_code,
            headers=headers
        )

    @staticmethod
    def error(
        message: str = None,
        metadata: Optional[Dict] = None,
        status_code: int = HTTP_500_INTERNAL_SERVER_ERROR,
    ) -> FAPIResponse:
        """
        Standard error response.
        
        Args:
            data: Main response payload
            message: Human-readable message
            metadata: Additional pagination/context data
            status_code: Appropriate 2xx status code
            headers: Custom HTTP headers
            
        Example:
            APIResponse.error(
                message='error occurred',
                metadata={'details': 'More info'},
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        """
        return FAPIResponse(
            {
                'status': ResponseStatus.SUCCESS.value,
                'message': message,
                'metadata': metadata or {}
            },
            status_code=status_code,
        )

    @staticmethod
    def paginated(
        data: List[Any],
        total: int,
        page: int,
        page_size: int,
        message: str = "Data retrieved successfully"
    ) -> FAPIResponse:
        
        
        
        return FAPIResponse(
            {
                'status': ResponseStatus.SUCCESS.value,
                'message': message,
                'data': data,
                'metadata': {
                    'pagination': {
                        'total': total,
                        'page': page,
                        'page_size': page_size,
                        'total_pages': (total + page_size - 1) // page_size
                    }
                }
            },
            status_code=HTTP_200_OK
        )

    @staticmethod
    def created(
        data: Any = None,
        message: str = "Resource created successfully",
        location: str = None,
        headers: Optional[Dict] = None
    ) -> FAPIResponse:
        """
        201 Created response with location header.
        
        Args:
            location: URI of the created resource
        """
        headers = headers or {}
        serialized_data = APIResponse._serialize_data(data)
        if location:
            headers['Location'] = location
        return FAPIResponse(
            {
                "status": ResponseStatus.SUCCESS.value,
                "message": message,
                "data": serialized_data
            },
            status_code=HTTP_201_CREATED,
            headers=headers
        )

    @staticmethod
    def no_content(headers: Optional[Dict] = None) -> Response:
        """
        204 No Content response for successful deletions/updates.
        """
        return Response(status_code=HTTP_204_NO_CONTENT, headers=headers)

    @staticmethod
    def bad_request(
        message: str = "Invalid request",
        errors: Optional[Dict] = None,
        code: Optional[str] = None
    ) -> FAPIResponse:
        """400 Bad Request with validation details."""
        return FAPIResponse(
            {
                "status": ResponseStatus.FAILURE.value,
                "code": code or "VALIDATION_ERROR",
                "message": message,
                "errors": errors or {}
            },
            status_code=HTTP_400_BAD_REQUEST
        )

    @staticmethod
    def unauthorized(
        message: str = "Authentication required",
        code: str = "AUTH_REQUIRED"
    ) -> FAPIResponse:
        """401 Unauthorized response."""
        return FAPIResponse(
            {
                "status": ResponseStatus.FAILURE.value,
                "code": code,
                "message": message
            },
            status_code=HTTP_401_UNAUTHORIZED
        )

    @staticmethod
    def forbidden(
        message: str = "Insufficient permissions",
        code: str = "PERMISSION_DENIED"
    ) -> FAPIResponse:
        """403 Forbidden response."""
        return FAPIResponse(
            {
                "status": ResponseStatus.FAILURE.value,
                "code": code,
                "message": message
            },
            status_code=HTTP_403_FORBIDDEN
        )

    @staticmethod
    def not_found(
        resource: str = "Resource",
        code: str = "NOT_FOUND"
    ) -> FAPIResponse:
        """404 Not Found response."""
        return FAPIResponse(
            {
                "status": ResponseStatus.FAILURE.value,
                "code": code,
                "message": f"{resource} not found"
            },
            status_code=HTTP_404_NOT_FOUND
        )

    @staticmethod
    def internal_error(
        message: str = "Internal server error",
        code: Optional[str] = "INTERNAL_ERROR"
    ) -> FAPIResponse:
        """500 Internal Server Error with optional tracking ID."""
        response = {
            "status": ResponseStatus.ERROR.value,
            "code": code,
            "message": message
        }
            
        return FAPIResponse(response, status_code=HTTP_500_INTERNAL_SERVER_ERROR)

    @staticmethod
    def conflict(
        message: str = "Resource conflict",
        code: str = "CONFLICT"
    ) -> FAPIResponse:
        """409 Conflict response."""
        return FAPIResponse(
            {
                "status": ResponseStatus.FAILURE.value,
                "code": code,
                "message": message
            },
            status_code=HTTP_409_CONFLICT
        )

    @staticmethod
    def not_implemented(
        feature: str = "This feature",
        code: str = "NOT_IMPLEMENTED",
        roadmap_link: str = None
    ) -> FAPIResponse:
        """
        501 Not Implemented response.
        """
        payload = {
            'status': ResponseStatus.ERROR.value,
            'code': code,
            'message': f"{feature} is not implemented yet"
        }
        if roadmap_link:
            payload['roadmap'] = roadmap_link
            
        return FAPIResponse(
            payload,
            status_code=HTTP_501_NOT_IMPLEMENTED
        )


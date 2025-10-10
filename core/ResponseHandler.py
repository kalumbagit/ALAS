from typing import Any, Dict, Optional, List
from fastapi.responses import JSONResponse as DRFResponse
from fastapi import Response

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
    def success(
        data: Any = None,
        message: str = None,
        metadata: Optional[Dict] = None,
        status_code: int = HTTP_200_OK,
        headers: Optional[Dict] = None
    ) -> DRFResponse:
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
        return DRFResponse(
            {
                'status': ResponseStatus.SUCCESS.value,
                'message': message,
                'data': data,
                'metadata': metadata or {}
            },
            status=status_code,
            headers=headers
        )

    @staticmethod
    def error(
        message: str = None,
        metadata: Optional[Dict] = None,
        status_code: int = HTTP_500_INTERNAL_SERVER_ERROR,
    ) -> DRFResponse:
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
        return DRFResponse(
            {
                'status': ResponseStatus.SUCCESS.value,
                'message': message,
                'metadata': metadata or {}
            },
            status=status_code,
        )

    @staticmethod
    def paginated(
        data: List[Any],
        total: int,
        page: int,
        page_size: int,
        message: str = "Data retrieved successfully"
    ) -> DRFResponse:
        
        return DRFResponse(
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
    ) -> DRFResponse:
        """
        201 Created response with location header.
        
        Args:
            location: URI of the created resource
        """
        headers = headers or {}
        if location:
            headers['Location'] = location
        return DRFResponse(
            {
                "status": ResponseStatus.SUCCESS.value,
                "message": message,
                "data": data
            },
            status=HTTP_201_CREATED,
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
    ) -> DRFResponse:
        """400 Bad Request with validation details."""
        return DRFResponse(
            {
                "status": ResponseStatus.FAILURE.value,
                "code": code or "VALIDATION_ERROR",
                "message": message,
                "errors": errors or {}
            },
            status=HTTP_400_BAD_REQUEST
        )

    @staticmethod
    def unauthorized(
        message: str = "Authentication required",
        code: str = "AUTH_REQUIRED"
    ) -> DRFResponse:
        """401 Unauthorized response."""
        return DRFResponse(
            {
                "status": ResponseStatus.FAILURE.value,
                "code": code,
                "message": message
            },
            status=HTTP_401_UNAUTHORIZED
        )

    @staticmethod
    def forbidden(
        message: str = "Insufficient permissions",
        code: str = "PERMISSION_DENIED"
    ) -> DRFResponse:
        """403 Forbidden response."""
        return DRFResponse(
            {
                "status": ResponseStatus.FAILURE.value,
                "code": code,
                "message": message
            },
            status=HTTP_403_FORBIDDEN
        )

    @staticmethod
    def not_found(
        resource: str = "Resource",
        code: str = "NOT_FOUND"
    ) -> DRFResponse:
        """404 Not Found response."""
        return DRFResponse(
            {
                "status": ResponseStatus.FAILURE.value,
                "code": code,
                "message": f"{resource} not found"
            },
            status=HTTP_404_NOT_FOUND
        )

    @staticmethod
    def internal_error(
        message: str = "Internal server error",
        code: Optional[str] = "INTERNAL_ERROR"
    ) -> DRFResponse:
        """500 Internal Server Error with optional tracking ID."""
        response = {
            "status": ResponseStatus.ERROR.value,
            "code": code,
            "message": message
        }
            
        return DRFResponse(response, status=HTTP_500_INTERNAL_SERVER_ERROR)

    @staticmethod
    def conflict(
        message: str = "Resource conflict",
        code: str = "CONFLICT"
    ) -> DRFResponse:
        """409 Conflict response."""
        return DRFResponse(
            {
                "status": ResponseStatus.FAILURE.value,
                "code": code,
                "message": message
            },
            status=HTTP_409_CONFLICT
        )

    @staticmethod
    def not_implemented(
        feature: str = "This feature",
        code: str = "NOT_IMPLEMENTED",
        roadmap_link: str = None
    ) -> DRFResponse:
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
            
        return DRFResponse(
            payload,
            status=HTTP_501_NOT_IMPLEMENTED
        )


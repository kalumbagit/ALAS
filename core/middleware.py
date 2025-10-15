# core/middleware.py
import time
from typing import Dict, Any
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from core.logging import logger
import uuid


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware de logging des requêtes HTTP
    """
    
    async def dispatch(self, request: Request, call_next):
        # Génération d'un ID de requête unique
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        start_time = time.time()
        
        # Log de la requête entrante
        logger.info(
            "Request started",
            extra={
                "request_id": request_id,
                "method": request.method,
                "url": str(request.url),
                "client_host": request.client.host if request.client else None,
                "user_agent": request.headers.get("user-agent")
            }
        )
        
        try:
            response = await call_next(request)
            process_time = time.time() - start_time
            
            # Log de la réponse
            logger.info(
                "Request completed",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "duration_ms": round(process_time * 1000, 2)
                }
            )
            
            # Ajout de l'ID de requête dans les headers
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Process-Time"] = str(process_time)
            
            return response
            
        except Exception as e:
            process_time = time.time() - start_time
            logger.error(
                "Request failed",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "duration_ms": round(process_time * 1000, 2),
                    "error": str(e),
                    "exception_type": type(e).__name__
                },
                exc_info=True
            )
            raise


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware de rate limiting basique
    """
    
    def __init__(self, app, calls: int = 100, period: int = 60):
        super().__init__(app)
        self.calls = calls
        self.period = period
        self.requests: Dict[str, list] = {}
    
    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host if request.client else "unknown"
        current_time = time.time()
        
        # Nettoyage des vieilles requêtes
        if client_ip in self.requests:
            self.requests[client_ip] = [
                req_time for req_time in self.requests[client_ip]
                if current_time - req_time < self.period
            ]
        
        # Vérification du rate limiting
        if client_ip in self.requests and len(self.requests[client_ip]) >= self.calls:
            logger.warning(
                "Rate limit exceeded",
                extra={
                    "client_ip": client_ip,
                    "calls": len(self.requests[client_ip]),
                    "limit": self.calls
                }
            )
            return Response(
                content='{"success": false, "error": {"code": 429, "message": "Too Many Requests"}}',
                status_code=429,
                media_type="application/json"
            )
        
        # Ajout de la requête actuelle
        if client_ip not in self.requests:
            self.requests[client_ip] = []
        self.requests[client_ip].append(current_time)
        
        return await call_next(request)
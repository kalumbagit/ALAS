# core/middleware.py
import time,json
from typing import List
from fastapi import Request,status
from starlette.middleware.base import BaseHTTPMiddleware
from core.logging import logger
import uuid
from core.redis import RedisService
from core.exceptions import APIException


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
        self.client = RedisService()
    
    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host if request.client else "unknown"
        current_time = time.time()

        try:
            # 🔹 1️⃣ Récupération des timestamps récents depuis Redis
            raw_data = await self.client.get_data(client_ip)
            request_times: List[float] = json.loads(raw_data) if raw_data else []

            # 🔹 2️⃣ Nettoyage : ne garder que les requêtes encore valides
            request_times = [
                ts for ts in request_times
                if current_time - ts < self.period
            ]

            # 🔹 3️⃣ Vérification du dépassement de quota
            if len(request_times) >= self.calls:
                logger.warning(
                    f"Rate limit exceeded for IP: {client_ip}",
                    extra={
                        "client_ip": client_ip,
                        "calls": len(request_times),
                        "limit": self.calls,
                        "period": self.period
                    }
                )

                raise APIException(status_code=status.HTTP_429_TOO_MANY_REQUESTS,detail="Too Many Requests")

            # 🔹 4️⃣ Ajout du timestamp de la requête actuelle
            request_times.append(current_time)

            # 🔹 5️⃣ Enregistrement dans Redis avec expiration automatique
            await self.client.set_data(
                key=client_ip,
                value=json.dumps(request_times),
                ttl=self.period
            )

            # 🔹 6️⃣ Continuer la requête
            return await call_next(request)

        except Exception as e:
            logger.error(f"Erreur RateLimitMiddleware: {e}", exc_info=True)
            # En cas d’erreur Redis → on ne bloque pas l’utilisateur
            return await call_next(request)
        


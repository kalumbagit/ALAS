# app/core/middlewares.py
from fastapi import FastAPI, Request, HTTPException
import time
from fastapi.responses import JSONResponse

import jwt  # PyJWT
from typing import Optional

from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.gzip import GZipMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.httpsredirect import HTTPSRedirectMiddleware
from starlette.middleware.sessions import SessionMiddleware

class AppMiddleware:
    """
    Classe pour centraliser l'ajout de middlewares FastAPI / Starlette.
    """

    def __init__(self, app: FastAPI):
        self.app = app

    def configure(self):
        """
        Ajoute tous les middlewares nécessaires à l'application.
        """
        # 🔹 CORS
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],  # À limiter en prod !
            allow_methods=["*"],
            allow_headers=["*"],
            allow_credentials=True
        )

        # 🔹 Compression GZip pour réponses > 1KB
        self.app.add_middleware(GZipMiddleware, minimum_size=1000)

        # 🔹 Hosts autorisés
        self.app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=["example.com", "*.example.org"]
        )

        # 🔹 Redirection HTTP -> HTTPS
        self.app.add_middleware(HTTPSRedirectMiddleware)

        # 🔹 Sessions côté serveur
        self.app.add_middleware(
            SessionMiddleware,
            secret_key="mon_secret_super_secure"
        )


class AppMiddleware:
    """
    Classe pour ajouter middlewares FastAPI :
    - Logging
    - JWT Auth
    """

    def __init__(self, app: FastAPI, jwt_secret: str):
        self.app = app
        self.jwt_secret = jwt_secret

    def configure(self):
        """Configure tous les middlewares nécessaires"""
        # Middleware logging + JWT
        @self.app.middleware("http")
        async def logging_and_jwt(request: Request, call_next):
            start_time = time.time()
            method = request.method
            url = str(request.url)

            # 🔹 JWT verification (sauf pour OPTIONS ou routes publiques)
            if not url.endswith("/login") and method != "OPTIONS":
                token: Optional[str] = request.headers.get("Authorization")
                if not token or not token.startswith("Bearer "):
                    return JSONResponse(
                        {"status": "failure", "message": "Missing JWT token"},
                        status_code=401
                    )
                token = token.split(" ")[1]
                try:
                    payload = jwt.decode(token, self.jwt_secret, algorithms=["HS256"])
                    # Tu peux stocker le payload pour tes routes
                    request.state.user = payload
                except jwt.ExpiredSignatureError:
                    return JSONResponse(
                        {"status": "failure", "message": "Token expired"},
                        status_code=401
                    )
                except jwt.InvalidTokenError:
                    return JSONResponse(
                        {"status": "failure", "message": "Invalid token"},
                        status_code=401
                    )

            # Appel de la route
            response = await call_next(request)

            # 🔹 Logging
            duration = time.time() - start_time
            print(f"[LOG] {method} {url} - {response.status_code} - {duration:.2f}s")

            return response

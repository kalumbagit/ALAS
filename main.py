# app/main.py
from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from contextlib import asynccontextmanager
import logging
from typing import Any, Dict

from fastapi import Security
from fastapi.security import HTTPBearer


from core.database import init_db, close_db
from core.config import settings
from core.logging import setup_logging, logger
from middlewares.middleware import LoggingMiddleware, RateLimitMiddleware

# Controllers
from controllers import (
    health_controller,
    category_controller,
    product_controller
)


# Configuration du logging
setup_logging()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Gestionnaire professionnel du cycle de vie de l'application
    """
    startup_logger = logging.getLogger("startup")
    
    try:
        # === PHASE DE DÉMARRAGE ===
        startup_logger.info("🚀 Démarrage de l'application...")
        
        # Initialisation de la base de données
        startup_logger.info("📊 Initialisation de la base de données...")
        await init_db(app)
        
        # Vérification de la configuration
        if not settings.JWT_SECRET or settings.JWT_SECRET == "your-super-secret-jwt-key-change-in-production":
            startup_logger.warning("⚠️  JWT_SECRET utilise la valeur par défaut - À CHANGER EN PRODUCTION")
        
        startup_logger.info(f"✅ Application {settings.APP_NAME} démarrée avec succès")
        startup_logger.info(f"📍 Environnement: {settings.APP_ENV}")
        startup_logger.info(f"🔧 Debug: {settings.DEBUG}")
        
        yield  # ⏩ L'application est prête à recevoir des requêtes
        
    except Exception as e:
        startup_logger.critical(f"❌ Erreur critique lors du démarrage: {str(e)}", exc_info=True)
        raise
    
    finally:
        # === PHASE D'ARRÊT ===
        shutdown_logger = logging.getLogger("shutdown")
        try:
            shutdown_logger.info("🛑 Arrêt de l'application en cours...")
            
            # Fermeture propre des connexions
            await close_db()
            
            shutdown_logger.info("✅ Application arrêtée proprement")
            
        except Exception as e:
            shutdown_logger.error(f"❌ Erreur lors de l'arrêt de l'application: {str(e)}", exc_info=True)

def create_application() -> FastAPI:
    """
    Factory pour créer l'instance FastAPI avec configuration professionnelle
    """
    # Configuration des métadonnées OpenAPI
    openapi_tags = [
        {
            "name": "Authentication",
            "description": "Endpoints d'authentification et gestion des tokens"
        },
        {
            "name": "Users", 
            "description": "Gestion des utilisateurs"
        },
        {
            "name": "Health",
            "description": "Vérification du statut de l'application"
        }
    ]
    
    # Création de l'application
    app = FastAPI(
        title=settings.APP_NAME,
        description="""
        API Professionnelle de Gestion d'Utilisateurs avec Authentification JWT.
        
        ## Fonctionnalités
        
        * 🔐 Authentification JWT sécurisée
        * 👥 Gestion complète des utilisateurs
        * 🛡️ Protection CORS et middleware de sécurité
        * 📊 Logging structuré
        * 🚀 Optimisé pour la production
        
        """,
        version=settings.APP_VERSION,
        debug=settings.DEBUG,
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None,
        openapi_url="/openapi.json" if settings.DEBUG else None,
        openapi_tags=openapi_tags,
        lifespan=lifespan,
        contact={
            "name": "Support Technique",
            "email": "support@example.com",
        },
        license_info={
            "name": "Proprietary",
            "url": "https://example.com/license",
        }
    )
    
    # Configuration des middlewares
    _setup_middlewares(app)
    
    # Configuration des routes
    _setup_routers(app)
    
    # Configuration des handlers d'erreurs
    _setup_exception_handlers(app)
    
    # --- Configuration Swagger pour JWT ---
    _setup_custom_openapi(app)

    return app

def _setup_middlewares(app: FastAPI) -> None:
    """
    Configuration des middlewares de sécurité et de monitoring
    """
    # CORS Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["X-Total-Count", "X-Request-ID"]
    )
    
    # Trusted Host Middleware
    if not settings.DEBUG:
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=settings.ALLOWED_HOSTS
        )
    
    # Logging Middleware (personnalisé)
    app.add_middleware(LoggingMiddleware)
    
    # Rate Limiting Middleware (en production)
    if settings.APP_ENV == "production":
        app.add_middleware(
            RateLimitMiddleware,
            calls=settings.RATE_LIMIT_CALLS,
            period=settings.RATE_LIMIT_PERIOD
        )

def _setup_routers(app: FastAPI) -> None:
    """
    Configuration des routeurs de l'application
    """
    # Routes API v1 (pour future versioning)
    app.include_router(
        health_controller.router,
        prefix=f"/{settings.APP_TYPE}/{settings.API_VERSION}/health",
        tags=["Health"]
    )
    
    app.include_router(
        category_controller.router,
        prefix=f"/{settings.APP_TYPE}/{settings.API_VERSION}"
    )
    
    app.include_router(
        product_controller.router,
        prefix=f"/{settings.APP_TYPE}/{settings.API_VERSION}"
    )
     
def _setup_exception_handlers(app: FastAPI) -> None:
    """
    Configuration des handlers d'exceptions globales
    """
    from fastapi import Request
    from fastapi.responses import JSONResponse
    from fastapi.exceptions import RequestValidationError
    from starlette.exceptions import HTTPException as StarletteHTTPException
    
    from core.exceptions import (
        APIException
    )
    
    @app.exception_handler(APIException)
    async def api_exception_handler(request: Request, exc: APIException):
        """Handler pour les exceptions métier personnalisées"""
        logger.warning(
            f"Exception métier: {exc.detail}",
            extra={
                "status_code": exc.status_code,
                "path": request.url.path,
                "method": request.method
            }
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "error": {
                    "code": exc.status_code,
                    "message": exc.detail,
                    "type": exc.__class__.__name__
                },
                "data": None
            }
        )
    
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """Handler pour les erreurs de validation Pydantic"""
        logger.warning(
            f"Erreur de validation: {exc.errors()}",
            extra={
                "path": request.url.path,
                "method": request.method,
                "errors": exc.errors()
            }
        )
        return JSONResponse(
            status_code=422,
            content={
                "success": False,
                "error": {
                    "code": 422,
                    "message": "Données de requête invalides",
                    "type": "ValidationError",
                    "details": exc.errors()
                },
                "data": None
            }
        )
    
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        """Handler pour les exceptions HTTP standard"""
        logger.warning(
            f"Exception HTTP: {exc.detail}",
            extra={
                "status_code": exc.status_code,
                "path": request.url.path,
                "method": request.method
            }
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "error": {
                    "code": exc.status_code,
                    "message": exc.detail,
                    "type": "HTTPException"
                },
                "data": None
            }
        )
    
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        """Handler global pour toutes les exceptions non gérées"""
        logger.error(
            f"Erreur interne du serveur: {str(exc)}",
            extra={
                "path": request.url.path,
                "method": request.method,
                "exception_type": exc.__class__.__name__
            },
            exc_info=True
        )
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": {
                    "code": 500,
                    "message": "Erreur interne du serveur",
                    "type": "InternalServerError"
                },
                "data": None
            }
        )

def _setup_custom_openapi(app: FastAPI) -> None:
    """
    Configure un schéma OpenAPI personnalisé avec support JWT.
    """

    def custom_openapi():
        if app.openapi_schema:
            return app.openapi_schema

        openapi_schema = get_openapi(
            title=app.title,
            version=app.version,
            description=app.description,
            routes=app.routes,
            contact=app.contact,
            license_info=app.license_info,
        )

        # --- 🔐 Définition des schémas de sécurité JWT ---
        openapi_schema["components"]["securitySchemes"] = {
            "AuthMiddleware": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT",
                "description": (
                    "🔑 **Access Token JWT** — requis pour accéder aux routes protégées.\n\n"
                    "Format : `Bearer <access_token>`"
                ),
            },
            "RefreshHeaderAuth": {
                "type": "apiKey",
                "in": "header",
                "name": "X-Refresh-Token",
                "description": (
                    "♻️ **Refresh Token JWT** — à fournir dans le header `X-Refresh-Token`.\n\n"
                    "Format : `<refresh_token>`"
                ),
            },
        }

        # --- 🔒 Appliquer le schéma globalement ---
        openapi_schema["security"] = [{"AuthMiddleware": []}]
        app.openapi_schema = openapi_schema
        return app.openapi_schema

    # ✅ Assignation correcte
    app.openapi = custom_openapi


# Instance de l'application
app = create_application()


# Routes racines supplémentaires
@app.get("/")
async def root() -> Dict[str, Any]:
    """
    Endpoint racine avec informations sur l'API
    """
    return {
        "success": True,
        "data": {
            "message": f"Bienvenue sur {settings.APP_NAME}",
            "version": settings.APP_VERSION,
            "APP_TYPE":settings.APP_TYPE,
            "API_VERSION":settings.API_VERSION,
            "APP_ENV": settings.APP_ENV,
            "status": "operational",
            "documentation": "/docs" if settings.DEBUG else None
        }
    }


@app.get("/favicon.ico")
async def favicon():
    """Endpoint favicon pour éviter les erreurs 404"""
    from fastapi.responses import Response
    return Response(status_code=204)


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8001,
        reload=settings.DEBUG,
        log_level="info",
        access_log=True
    )
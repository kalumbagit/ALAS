import logging
import sys
import json
from datetime import datetime,timezone
from pathlib import Path
from typing import Dict, Any, Optional
import os

from core.config import settings


class JSONFormatter(logging.Formatter):
    """
    Formateur de logs en JSON pour une meilleure intégration avec les systèmes de monitoring
    """
    
    def format(self, record: logging.LogRecord) -> str:
        """
        Format le log en JSON
        """
        log_data = {
            "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Ajout des données supplémentaires si présentes
        if hasattr(record, "extra_data"):
            log_data.update(record.extra_data)
            
        # Gestion des exceptions
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
            
        return json.dumps(log_data, ensure_ascii=False)


class ColorFormatter(logging.Formatter):
    """
    Formateur de logs avec couleurs pour la console (développement)
    """
    
    # Codes de couleurs ANSI
    GREY = "\x1b[38;20m"
    GREEN = "\x1b[32;20m"
    YELLOW = "\x1b[33;20m"
    RED = "\x1b[31;20m"
    BOLD_RED = "\x1b[31;1m"
    BLUE = "\x1b[34;20m"
    RESET = "\x1b[0m"
    
    # Mapping niveau -> couleur
    LEVEL_COLORS = {
        logging.DEBUG: BLUE,
        logging.INFO: GREEN,
        logging.WARNING: YELLOW,
        logging.ERROR: RED,
        logging.CRITICAL: BOLD_RED,
    }
    
    def format(self, record: logging.LogRecord) -> str:
        """
        Format le log avec des couleurs
        """
        color = self.LEVEL_COLORS.get(record.levelno, self.GREY)
        
        # Format de base avec couleur
        format_str = f"{color}%(asctime)s - %(name)s - %(levelname)s - %(message)s{self.RESET}"
        formatter = logging.Formatter(format_str, datefmt="%Y-%m-%d %H:%M:%S")
        
        # Gestion des exceptions
        if record.exc_info:
            formatted = formatter.format(record)
            formatted += f"\n{color}{self.formatException(record.exc_info)}{self.RESET}"
            return formatted
            
        return formatter.format(record)


class ContextFilter(logging.Filter):
    """
    Filtre pour ajouter des informations contextuelles aux logs
    """
    
    def filter(self, record: logging.LogRecord) -> bool:
        """
        Ajoute des informations contextuelles au record
        """
        # Informations de base
        record.environment = settings.APP_ENV
        record.app_name = settings.APP_NAME
        record.app_version = settings.APP_VERSION
        
        # Timestamp en format ISO
        record.iso_timestamp = datetime.now(timezone.utc).isoformat() + "Z"
        
        return True


def setup_logging() -> None:
    """
    Configure le système de logging selon l'environnement
    """
    # Création du dossier de logs s'il n'existe pas
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Niveau de log selon l'environnement
    if settings.APP_ENV == "development":
        log_level = logging.DEBUG
    elif settings.APP_ENV == "testing":
        log_level = logging.INFO
    else:  # production
        log_level = logging.WARNING
    
    # Configuration du logger racine
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Suppression des handlers existants
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Filtre de contexte
    context_filter = ContextFilter()
    
    # Handler pour la console
    console_handler = logging.StreamHandler(sys.stdout)
    if settings.APP_ENV == "development":
        console_handler.setFormatter(ColorFormatter())
    else:
        console_handler.setFormatter(JSONFormatter())
    console_handler.addFilter(context_filter)
    root_logger.addHandler(console_handler)
    
    # Handler pour les fichiers (uniquement en production/staging)
    if settings.APP_ENV in ["production", "staging"]:
        # Fichier pour tous les logs
        file_handler = logging.FileHandler(
            log_dir / f"{settings.APP_NAME}.log",
            encoding="utf-8"
        )
        file_handler.setFormatter(JSONFormatter())
        file_handler.addFilter(context_filter)
        file_handler.setLevel(logging.INFO)
        root_logger.addHandler(file_handler)
        
        # Fichier séparé pour les erreurs
        error_handler = logging.FileHandler(
            log_dir / f"{settings.APP_NAME}.errors.log",
            encoding="utf-8"
        )
        error_handler.setFormatter(JSONFormatter())
        error_handler.addFilter(context_filter)
        error_handler.setLevel(logging.ERROR)
        root_logger.addHandler(error_handler)
    
    # Handler spécifique pour les requêtes HTTP en développement
    if settings.APP_ENV == "development":
        access_handler = logging.FileHandler(
            log_dir / "access.log",
            encoding="utf-8"
        )
        access_handler.setFormatter(
            logging.Formatter('%(asctime)s - %(message)s')
        )
        access_logger = logging.getLogger("uvicorn.access")
        access_logger.addHandler(access_handler)
        access_logger.setLevel(logging.INFO)
    
    # Configuration spécifique pour les librairies externes
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("tortoise").setLevel(logging.WARNING)
    logging.getLogger("aiosqlite").setLevel(logging.WARNING)
    
    # Log de démarrage
    logger = logging.getLogger(__name__)
    logger.info(
        "Logging configuré",
        extra={
            "environment": settings.APP_ENV,
            "log_level": logging.getLevelName(log_level),
            "app_name": settings.APP_NAME,
            "app_version": settings.APP_VERSION
        }
    )


class Logger:
    """
    Logger personnalisé avec des méthodes utilitaires
    """
    
    def __init__(self, name: str = None):
        self.logger = logging.getLogger(name or __name__)
    
    def debug(self, message: str, **kwargs) -> None:
        """Log niveau DEBUG"""
        self.logger.debug(message, extra={"extra_data": kwargs})
    
    def info(self, message: str, **kwargs) -> None:
        """Log niveau INFO"""
        self.logger.info(message, extra={"extra_data": kwargs})
    
    def warning(self, message: str, **kwargs) -> None:
        """Log niveau WARNING"""
        self.logger.warning(message, extra={"extra_data": kwargs})
    
    def error(self, message: str, **kwargs) -> None:
        """Log niveau ERROR"""
        self.logger.error(message, extra={"extra_data": kwargs})
    
    def critical(self, message: str, **kwargs) -> None:
        """Log niveau CRITICAL"""
        self.logger.critical(message, extra={"extra_data": kwargs})
    
    def exception(self, message: str, **kwargs) -> None:
        """Log une exception avec stack trace"""
        full_message = f"{message} | extra: {kwargs}" if kwargs else message
        self.logger.exception(full_message)
    
    # Méthodes métier spécifiques
    def api_request(self, method: str, path: str, status_code: int, duration: float, **kwargs) -> None:
        """Log une requête API"""
        self.info(
            f"API {method} {path} - {status_code} - {duration:.3f}s",
            method=method,
            path=path,
            status_code=status_code,
            duration_ms=round(duration * 1000),
            **kwargs
        )
    
    def database_query(self, query: str, duration: float, **kwargs) -> None:
        """Log une requête base de données"""
        self.debug(
            f"Database query executed in {duration:.3f}s",
            query=query,
            duration_ms=round(duration * 1000),
            **kwargs
        )
    
    def user_activity(self, user_id: str, action: str, **kwargs) -> None:
        """Log une activité utilisateur"""
        self.info(
            f"User activity: {action}",
            user_id=user_id,
            action=action,
            **kwargs
        )
    
    def security_event(self, event_type: str, severity: str, **kwargs) -> None:
        """Log un événement de sécurité"""
        log_method = {
            "low": self.info,
            "medium": self.warning,
            "high": self.error,
            "critical": self.critical
        }.get(severity, self.warning)
        
        log_method(
            f"Security event: {event_type}",
            event_type=event_type,
            severity=severity,
            **kwargs
        )


# Instance globale du logger
logger = Logger()

# Middleware de logging pour FastAPI (optionnel)
async def log_requests_middleware(request, call_next):
    """
    Middleware pour logger les requêtes HTTP
    """
    import time
    start_time = time.time()
    
    # Log de la requête entrante
    logger.debug(
        "Request started",
        method=request.method,
        url=str(request.url),
        client_host=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )
    
    try:
        response = await call_next(request)
        duration = time.time() - start_time
        
        # Log de la réponse
        logger.api_request(
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration=duration,
            client_host=request.client.host if request.client else None
        )
        
        return response
        
    except Exception as e:
        duration = time.time() - start_time
        logger.error(
            f"Request failed: {str(e)}",
            method=request.method,
            url=str(request.url),
            duration=duration,
            exception_type=type(e).__name__
        )
        raise


# Configuration automatique au chargement du module
if not logging.getLogger().handlers:
    setup_logging()
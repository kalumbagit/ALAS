# controllers/health_controller.py
from fastapi import APIRouter, Depends
from tortoise.transactions import in_transaction
from core.database import get_db
from core.logging import logger
from datetime import datetime, timezone

router = APIRouter()

@router.get("/")
async def health_check():
    """
    Health check basique de l'application
    """
    return {
        "success": True,
        "data": {
            "status": "healthy",
            "message": "Service opérationnel"
        }
    }

@router.get("/detailed")
async def detailed_health_check(db=Depends(get_db)):
    """
    Health check détaillé avec vérification de la base de données
    """
    try:
        # Test de connexion à la base de données
        async with in_transaction():
            db_status = "healthy"
            await db.execute_query("SELECT 1")
        
    except Exception as e:
        db_status = "unhealthy"
        logger.error(f"Database health check failed: {str(e)}")
    
    return {
        "success": True,
        "data": {
            "status": "healthy",
            "service": "operational",
            "database": db_status,
            "timestamp": datetime.now(timezone.utc)  # Utiliser datetime.utcnow() en réel
        }
    }
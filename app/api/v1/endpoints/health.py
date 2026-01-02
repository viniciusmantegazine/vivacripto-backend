"""
Health check API endpoint
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.db.base import get_db

router = APIRouter()


@router.get("")
async def health_check(db: AsyncSession = Depends(get_db)):
    """
    Health check endpoint - verifies API and database connectivity
    """
    try:
        # Test database connection
        await db.execute(text("SELECT 1"))
        db_status = "healthy"
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"
    
    return {
        "status": "healthy" if db_status == "healthy" else "degraded",
        "database": db_status,
    }

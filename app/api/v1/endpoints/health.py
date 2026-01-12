"""
Health check API endpoint
Provides detailed health status of the API and its dependencies.
"""
from datetime import datetime, timezone
from typing import Any, Dict

import httpx
import redis.asyncio as redis
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.base import get_db

router = APIRouter()


async def check_database(db: AsyncSession) -> Dict[str, Any]:
    """Check PostgreSQL database connectivity."""
    try:
        result = await db.execute(text("SELECT 1"))
        result.scalar()
        return {"status": "healthy", "latency_ms": None}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


async def check_redis() -> Dict[str, Any]:
    """Check Redis connectivity."""
    if not settings.REDIS_URL:
        return {"status": "not_configured"}

    try:
        client = redis.from_url(settings.REDIS_URL, decode_responses=True)
        await client.ping()
        await client.aclose()
        return {"status": "healthy"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


async def check_openai() -> Dict[str, Any]:
    """Check OpenAI API key configuration (does not make API call)."""
    if not settings.OPENAI_API_KEY or settings.OPENAI_API_KEY == "sk-...":
        return {"status": "not_configured"}
    return {"status": "configured"}


async def check_cloudinary() -> Dict[str, Any]:
    """Check Cloudinary configuration."""
    if not all([
        settings.CLOUDINARY_CLOUD_NAME,
        settings.CLOUDINARY_API_KEY,
        settings.CLOUDINARY_API_SECRET,
    ]):
        return {"status": "not_configured"}
    return {"status": "configured"}


async def check_frontend() -> Dict[str, Any]:
    """Check frontend connectivity for ISR revalidation."""
    if not settings.FRONTEND_URL:
        return {"status": "not_configured"}

    try:
        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.get(f"{settings.FRONTEND_URL}/api/health")
            if response.status_code == 200:
                return {"status": "healthy"}
            return {"status": "degraded", "http_status": response.status_code}
    except httpx.TimeoutException:
        return {"status": "timeout"}
    except Exception as e:
        return {"status": "unreachable", "error": str(e)}


@router.get("")
async def health_check(db: AsyncSession = Depends(get_db)):
    """
    Basic health check endpoint.
    Returns minimal status for load balancer health checks.
    """
    try:
        await db.execute(text("SELECT 1"))
        db_status = "healthy"
    except Exception:
        db_status = "unhealthy"

    overall = "healthy" if db_status == "healthy" else "degraded"

    return {
        "status": overall,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/ready")
async def readiness_check(db: AsyncSession = Depends(get_db)):
    """
    Kubernetes-style readiness probe.
    Returns 200 if the service is ready to receive traffic.
    Returns 503 if critical dependencies are unhealthy.
    """
    from fastapi.responses import JSONResponse

    database = await check_database(db)
    redis_status = await check_redis()

    db_ready = database.get("status") == "healthy"
    redis_ready = redis_status.get("status") in ("healthy", "not_configured")

    if db_ready and redis_ready:
        return {"status": "ready", "timestamp": datetime.now(timezone.utc).isoformat()}

    return JSONResponse(
        status_code=503,
        content={
            "status": "not_ready",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "checks": {
                "database": database,
                "redis": redis_status,
            },
        },
    )


@router.get("/live")
async def liveness_check():
    """
    Kubernetes-style liveness probe.
    Returns 200 if the process is alive.
    This is a lightweight check that doesn't hit external services.
    """
    return {"status": "alive", "timestamp": datetime.now(timezone.utc).isoformat()}


@router.get("/detailed")
async def detailed_health_check(db: AsyncSession = Depends(get_db)):
    """
    Detailed health check endpoint.
    Checks all external dependencies and returns comprehensive status.

    Use for monitoring and debugging - not for load balancer health checks
    as this endpoint is slower due to multiple external checks.
    """
    # Run all checks
    database = await check_database(db)
    redis_status = await check_redis()
    openai = await check_openai()
    cloudinary = await check_cloudinary()
    frontend = await check_frontend()

    # Determine overall status
    critical_services = [database]
    optional_services = [redis_status, openai, cloudinary, frontend]

    critical_healthy = all(s.get("status") == "healthy" for s in critical_services)
    optional_issues = sum(
        1 for s in optional_services
        if s.get("status") not in ("healthy", "configured", "not_configured")
    )

    if not critical_healthy:
        overall = "unhealthy"
    elif optional_issues > 0:
        overall = "degraded"
    else:
        overall = "healthy"

    return {
        "status": overall,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": settings.VERSION,
        "environment": "production" if not settings.DEBUG else "development",
        "services": {
            "database": database,
            "redis": redis_status,
            "openai": openai,
            "cloudinary": cloudinary,
            "frontend": frontend,
        },
    }

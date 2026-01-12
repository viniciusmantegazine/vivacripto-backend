"""
VivaCripto API - FastAPI Backend
Main application entry point
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager

from app.core.config import settings
from app.api.v1.api import api_router
from app.core.logging import setup_logging, logger
from app.core.rate_limiter import setup_rate_limiting

# Setup logging
setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    logger.info("Iniciando VivaCripto API...")
    yield
    # Shutdown
    logger.info("Encerrando VivaCripto API...")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="API para o portal de notícias VivaCripto",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
    lifespan=lifespan,
)

# Rate limiting (deve vir antes dos outros middlewares)
setup_rate_limiting(app)

# CORS middleware - métodos e headers restritos por segurança
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=[
        "Authorization",
        "Content-Type",
        "Accept",
        "Origin",
        "X-Requested-With",
    ],
    expose_headers=["X-RateLimit-Limit", "X-RateLimit-Remaining", "Retry-After"],
)

# Include API router
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/")
async def root():
    """Root endpoint"""
    return JSONResponse(
        content={
            "message": "VivaCripto API",
            "version": settings.VERSION,
            "docs": f"{settings.API_V1_STR}/docs",
        }
    )


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return JSONResponse(content={"status": "healthy"})


@app.exception_handler(404)
async def not_found_handler(request, exc):
    """Custom 404 handler"""
    return JSONResponse(
        status_code=404,
        content={
            "message": "Endpoint not found",
            "available_endpoints": {
                "root": "/",
                "health": "/health",
                "api_docs": f"{settings.API_V1_STR}/docs",
                "api_health": f"{settings.API_V1_STR}/health",
                "api_posts": f"{settings.API_V1_STR}/posts",
            }
        }
    )

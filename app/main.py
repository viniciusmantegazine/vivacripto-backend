"""
VivaCripto API - FastAPI Backend
Main application entry point
"""
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from app.api.v1.api import api_router
from app.core.config import settings
from app.core.exceptions import AppException
from app.core.logging import logger, set_request_context, setup_logging
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


# =============================================================================
# Global Exception Handlers
# =============================================================================


@app.middleware("http")
async def request_context_middleware(request: Request, call_next):
    """Add request ID to logging context for tracing."""
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4())[:8])
    set_request_context(request_id=request_id)
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    """Handler for application-specific exceptions."""
    logger.warning(
        f"Application error: {exc.detail}",
        extra={"status_code": exc.status_code, "path": request.url.path}
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail},
        headers=exc.headers,
    )


@app.exception_handler(ValidationError)
async def validation_exception_handler(request: Request, exc: ValidationError):
    """Handler for Pydantic validation errors."""
    logger.warning(
        f"Validation error: {exc.error_count()} errors",
        extra={"path": request.url.path, "errors": exc.errors()}
    )
    return JSONResponse(
        status_code=422,
        content={
            "error": "Validation error",
            "details": exc.errors(),
        },
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Global exception handler for unhandled exceptions.
    Logs the error and returns a generic error response in production.
    """
    logger.exception(
        f"Unhandled exception: {type(exc).__name__}: {exc}",
        extra={"path": request.url.path}
    )

    # Em produção, não expor detalhes do erro
    if settings.DEBUG:
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "detail": str(exc),
                "type": type(exc).__name__,
            },
        )

    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error"},
    )


# Include API router
app.include_router(api_router, prefix=settings.API_V1_STR)


# =============================================================================
# Root Endpoints
# =============================================================================


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

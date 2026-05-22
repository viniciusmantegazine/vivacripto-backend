"""
Database configuration and session management
"""
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.db.base_class import Base  # noqa: F401

# Create async engine with optimized pool settings
_url = settings.DATABASE_URL
_engine_kwargs: dict = {
    "echo": settings.DEBUG,  # Log SQL only in debug mode
    "future": True,
}
if not _url.startswith("sqlite"):
    _engine_kwargs["pool_pre_ping"] = True  # Test connections before use
    _engine_kwargs["pool_size"] = settings.DB_POOL_SIZE
    _engine_kwargs["max_overflow"] = settings.DB_MAX_OVERFLOW
    _engine_kwargs["pool_timeout"] = settings.DB_POOL_TIMEOUT
    _engine_kwargs["pool_recycle"] = settings.DB_POOL_RECYCLE
    _engine_kwargs["connect_args"] = {
        "server_settings": {"application_name": "vivacripto-api"},
        "timeout": 10,
        # Prepared statements for better performance
        "prepared_statement_cache_size": 256,
    }
engine = create_async_engine(_url, **_engine_kwargs)

# Create async session factory
AsyncSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncSession:
    """
    Dependency to get database session.

    Usage:
        @router.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def get_db_context():
    """
    Get database session as async context manager.

    Usage:
        async with get_db_context() as db:
            ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

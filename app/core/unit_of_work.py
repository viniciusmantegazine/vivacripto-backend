"""
Unit of Work pattern implementation for atomic transactions.
Provides a context manager for managing database transactions atomically.
"""
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import AsyncSessionLocal
from app.core.logging import logger


class UnitOfWork:
    """
    Unit of Work pattern for atomic database transactions.

    Manages the lifecycle of a database session and ensures that all operations
    within a transaction are committed together or rolled back on failure.

    Usage:
        async with UnitOfWork() as uow:
            # All operations within this block are part of the same transaction
            await uow.session.add(entity)
            await uow.commit()

        # Or with auto-commit on success:
        async with UnitOfWork(auto_commit=True) as uow:
            await uow.session.add(entity)
            # Commits automatically if no exception is raised
    """

    def __init__(self, auto_commit: bool = False):
        """
        Initialize the Unit of Work.

        Args:
            auto_commit: If True, automatically commits on successful exit.
                        If False, requires explicit commit() call.
        """
        self.auto_commit = auto_commit
        self._session: AsyncSession | None = None

    @property
    def session(self) -> AsyncSession:
        """Get the current database session."""
        if self._session is None:
            raise RuntimeError("UnitOfWork must be used as a context manager")
        return self._session

    async def __aenter__(self) -> "UnitOfWork":
        """Enter the context manager and create a new session."""
        self._session = AsyncSessionLocal()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit the context manager, handling commit/rollback."""
        if self._session is None:
            return

        try:
            if exc_type is not None:
                # An exception occurred, rollback
                logger.warning(f"Rolling back transaction due to: {exc_type.__name__}: {exc_val}")
                await self.rollback()
            elif self.auto_commit:
                # No exception and auto_commit is enabled
                await self.commit()
        finally:
            await self._session.close()
            self._session = None

    async def commit(self) -> None:
        """Commit the current transaction."""
        if self._session is None:
            raise RuntimeError("No active session to commit")
        try:
            await self._session.commit()
            logger.debug("Transaction committed successfully")
        except Exception as e:
            logger.error(f"Failed to commit transaction: {e}")
            await self.rollback()
            raise

    async def rollback(self) -> None:
        """Rollback the current transaction."""
        if self._session is None:
            return
        try:
            await self._session.rollback()
            logger.debug("Transaction rolled back")
        except Exception as e:
            logger.error(f"Failed to rollback transaction: {e}")
            raise

    async def refresh(self, instance) -> None:
        """Refresh an instance from the database."""
        if self._session is None:
            raise RuntimeError("No active session")
        await self._session.refresh(instance)


async def get_uow() -> AsyncGenerator[UnitOfWork, None]:
    """
    Dependency for FastAPI endpoints that need atomic transactions.

    Usage:
        @router.post("/items")
        async def create_item(uow: UnitOfWork = Depends(get_uow)):
            async with uow:
                # ... perform operations
                await uow.commit()
    """
    uow = UnitOfWork()
    try:
        yield uow
    finally:
        if uow._session is not None:
            await uow._session.close()

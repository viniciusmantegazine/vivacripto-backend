"""
Generic Repository Pattern interfaces.
Provides abstraction for data persistence operations.
"""
from abc import ABC, abstractmethod
from typing import Generic, List, Optional, TypeVar
from uuid import UUID

# Type variables for generic repository
T = TypeVar("T")  # Entity type
CreateSchema = TypeVar("CreateSchema")  # Create schema type
UpdateSchema = TypeVar("UpdateSchema")  # Update schema type


class BaseRepository(ABC, Generic[T, CreateSchema, UpdateSchema]):
    """
    Abstract base repository defining standard CRUD operations.

    This interface allows for easy swapping of data sources (database,
    cache, external API) and facilitates testing with mock implementations.

    Type Parameters:
        T: The entity/model type
        CreateSchema: The schema used for creating entities
        UpdateSchema: The schema used for updating entities
    """

    @abstractmethod
    async def get_by_id(self, entity_id: UUID) -> Optional[T]:
        """
        Retrieve an entity by its unique identifier.

        Args:
            entity_id: The unique identifier of the entity

        Returns:
            The entity if found, None otherwise
        """
        pass

    @abstractmethod
    async def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[List[T], int]:
        """
        Retrieve all entities with pagination.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            Tuple of (list of entities, total count)
        """
        pass

    @abstractmethod
    async def create(self, entity_in: CreateSchema) -> T:
        """
        Create a new entity.

        Args:
            entity_in: The creation schema with entity data

        Returns:
            The created entity
        """
        pass

    @abstractmethod
    async def update(self, entity_id: UUID, entity_in: UpdateSchema) -> Optional[T]:
        """
        Update an existing entity.

        Args:
            entity_id: The unique identifier of the entity to update
            entity_in: The update schema with new data

        Returns:
            The updated entity if found, None otherwise
        """
        pass

    @abstractmethod
    async def delete(self, entity_id: UUID) -> bool:
        """
        Delete an entity.

        Args:
            entity_id: The unique identifier of the entity to delete

        Returns:
            True if deleted successfully, False if entity not found
        """
        pass


class ReadOnlyRepository(ABC, Generic[T]):
    """
    Read-only repository interface for entities that shouldn't be modified
    through the application (e.g., reference data, audit logs).
    """

    @abstractmethod
    async def get_by_id(self, entity_id: UUID) -> Optional[T]:
        """Retrieve an entity by its unique identifier."""
        pass

    @abstractmethod
    async def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[List[T], int]:
        """Retrieve all entities with pagination."""
        pass

    @abstractmethod
    async def exists(self, entity_id: UUID) -> bool:
        """Check if an entity exists."""
        pass


class CacheableRepository(BaseRepository[T, CreateSchema, UpdateSchema]):
    """
    Extended repository interface with caching support.
    Implementations should handle cache invalidation on mutations.
    """

    @abstractmethod
    async def get_by_id_cached(
        self,
        entity_id: UUID,
        ttl_seconds: int = 300,
    ) -> Optional[T]:
        """
        Retrieve an entity with caching.

        Args:
            entity_id: The unique identifier
            ttl_seconds: Cache time-to-live in seconds

        Returns:
            The entity if found, None otherwise
        """
        pass

    @abstractmethod
    async def invalidate_cache(self, entity_id: UUID) -> None:
        """
        Invalidate cache for a specific entity.

        Args:
            entity_id: The unique identifier of the entity
        """
        pass

    @abstractmethod
    async def invalidate_all_cache(self) -> None:
        """Invalidate all cached entries for this repository."""
        pass

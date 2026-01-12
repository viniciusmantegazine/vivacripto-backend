"""
CRUD operations for Post model
"""
import re
from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import Post, Tag
from app.schemas.post import PostCreate, PostUpdate


def sanitize_search_query(query: str) -> str:
    """
    Sanitiza a query de busca para evitar ataques de wildcard DoS.
    Remove ou escapa caracteres especiais do SQL LIKE.

    Args:
        query: String de busca fornecida pelo usuário

    Returns:
        String sanitizada segura para uso em ILIKE
    """
    if not query:
        return ""

    # Remove espaços extras
    query = query.strip()

    # Escapa caracteres especiais do LIKE (%, _, \)
    query = query.replace("\\", "\\\\")
    query = query.replace("%", "\\%")
    query = query.replace("_", "\\_")

    # Remove caracteres de controle e não-imprimíveis
    query = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', query)

    # Limita o tamanho para evitar queries muito pesadas
    max_length = 200
    if len(query) > max_length:
        query = query[:max_length]

    return query


async def get_recent_posts(db: AsyncSession, since: datetime) -> List[Post]:
    """Get posts created since a specific date."""
    result = await db.execute(
        select(Post)
        .options(
            selectinload(Post.author),
            selectinload(Post.category),
            selectinload(Post.tags),
        )
        .where(Post.created_at >= since)
        .order_by(Post.created_at.desc())
    )
    return list(result.scalars().all())


async def get_post_by_id(db: AsyncSession, post_id: UUID) -> Optional[Post]:
    """Get a post by ID"""
    result = await db.execute(
        select(Post)
        .options(selectinload(Post.author), selectinload(Post.category), selectinload(Post.tags))
        .where(Post.id == post_id)
    )
    return result.scalar_one_or_none()


async def get_post_by_slug(db: AsyncSession, slug: str) -> Optional[Post]:
    """Get a post by slug"""
    result = await db.execute(
        select(Post)
        .options(selectinload(Post.author), selectinload(Post.category), selectinload(Post.tags))
        .where(Post.slug == slug)
    )
    return result.scalar_one_or_none()


async def get_posts(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 10,
    status: Optional[str] = None,
    category_id: Optional[UUID] = None,
) -> tuple[List[Post], int]:
    """Get posts with pagination and filters"""
    query = select(Post).options(
        selectinload(Post.author),
        selectinload(Post.category),
        selectinload(Post.tags)
    )
    
    # Apply filters
    if status:
        query = query.where(Post.status == status)
    if category_id:
        query = query.where(Post.category_id == category_id)
    
    # Order by published_at desc
    query = query.order_by(Post.published_at.desc())
    
    # Get total count
    count_query = select(func.count()).select_from(Post)
    if status:
        count_query = count_query.where(Post.status == status)
    if category_id:
        count_query = count_query.where(Post.category_id == category_id)
    
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Apply pagination
    query = query.offset(skip).limit(limit)
    
    result = await db.execute(query)
    posts = result.scalars().all()
    
    return posts, total


async def create_post(db: AsyncSession, post_in: PostCreate, auto_commit: bool = True) -> Post:
    """
    Create a new post.

    Args:
        db: Database session
        post_in: Post data
        auto_commit: If True, commits transaction automatically. Set to False
                     when using within a larger transaction (Unit of Work pattern).
    """
    # Extract tag IDs
    tag_ids = post_in.tag_ids if hasattr(post_in, 'tag_ids') else []

    # Create post dict without tag_ids
    post_dict = post_in.model_dump(exclude={'tag_ids'})

    # Set published_at if status is published
    if post_dict.get('status') == 'published' and not post_dict.get('published_at'):
        post_dict['published_at'] = datetime.now(timezone.utc)

    # Create post
    db_post = Post(**post_dict)

    # Add tags if provided
    if tag_ids:
        tag_result = await db.execute(select(Tag).where(Tag.id.in_(tag_ids)))
        tags = tag_result.scalars().all()
        db_post.tags = tags

    db.add(db_post)

    if auto_commit:
        await db.commit()
        await db.refresh(db_post)

    return db_post


async def update_post(
    db: AsyncSession, post_id: UUID, post_in: PostUpdate, auto_commit: bool = True
) -> Optional[Post]:
    """
    Update a post.

    Args:
        db: Database session
        post_id: Post ID to update
        post_in: Update data
        auto_commit: If True, commits transaction automatically. Set to False
                     when using within a larger transaction (Unit of Work pattern).
    """
    db_post = await get_post_by_id(db, post_id)
    if not db_post:
        return None

    update_data = post_in.model_dump(exclude_unset=True)

    # Update published_at if status changes to published
    if update_data.get('status') == 'published' and db_post.status != 'published':
        update_data['published_at'] = datetime.now(timezone.utc)

    for field, value in update_data.items():
        setattr(db_post, field, value)

    if auto_commit:
        await db.commit()
        await db.refresh(db_post)

    return db_post


async def delete_post(db: AsyncSession, post_id: UUID) -> bool:
    """Delete a post"""
    db_post = await get_post_by_id(db, post_id)
    if not db_post:
        return False
    
    await db.delete(db_post)
    await db.commit()
    
    return True


async def search_posts(db: AsyncSession, query: str, limit: int = 10) -> List[Post]:
    """
    Search posts by title or content.
    A query é sanitizada para prevenir ataques de wildcard DoS.
    """
    # Sanitiza a query para evitar ataques
    safe_query = sanitize_search_query(query)

    # Se a query ficou vazia após sanitização, retorna lista vazia
    if not safe_query:
        return []

    search_query = select(Post).options(
        selectinload(Post.author),
        selectinload(Post.category),
        selectinload(Post.tags)
    ).where(
        or_(
            Post.title.ilike(f"%{safe_query}%"),
            Post.content_markdown.ilike(f"%{safe_query}%")
        )
    ).where(Post.status == 'published').limit(limit)

    result = await db.execute(search_query)
    return list(result.scalars().all())


class CRUDPost:
    """CRUD operations class for Post"""
    
    async def get_recent_posts(self, db: AsyncSession, since: datetime) -> List[Post]:
        return await get_recent_posts(db, since)
    
    async def get_post_by_id(self, db: AsyncSession, post_id: UUID) -> Optional[Post]:
        return await get_post_by_id(db, post_id)
    
    async def get_post_by_slug(self, db: AsyncSession, slug: str) -> Optional[Post]:
        return await get_post_by_slug(db, slug)
    
    async def get_posts(
        self,
        db: AsyncSession,
        skip: int = 0,
        limit: int = 10,
        status: Optional[str] = None,
        category_id: Optional[UUID] = None,
    ) -> tuple[List[Post], int]:
        return await get_posts(db, skip, limit, status, category_id)
    
    async def create_post(
        self, db: AsyncSession, post_in: PostCreate, auto_commit: bool = True
    ) -> Post:
        return await create_post(db, post_in, auto_commit)

    async def update_post(
        self, db: AsyncSession, post_id: UUID, post_in: PostUpdate, auto_commit: bool = True
    ) -> Optional[Post]:
        return await update_post(db, post_id, post_in, auto_commit)
    
    async def delete_post(self, db: AsyncSession, post_id: UUID) -> bool:
        return await delete_post(db, post_id)
    
    async def search_posts(self, db: AsyncSession, query: str, limit: int = 10) -> List[Post]:
        return await search_posts(db, query, limit)


# Instância global para ser importada
crud_post = CRUDPost()

"""
CRUD operations for Post model
"""
from typing import List, Optional
from uuid import UUID
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from datetime import datetime

from app.db.models import Post, Tag
from app.schemas.post import PostCreate, PostUpdate


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


async def create_post(db: AsyncSession, post_in: PostCreate) -> Post:
    """Create a new post"""
    # Extract tag IDs
    tag_ids = post_in.tag_ids if hasattr(post_in, 'tag_ids') else []
    
    # Create post dict without tag_ids
    post_dict = post_in.model_dump(exclude={'tag_ids'})
    
    # Set published_at if status is published
    if post_dict.get('status') == 'published' and not post_dict.get('published_at'):
        post_dict['published_at'] = datetime.utcnow()
    
    # Create post
    db_post = Post(**post_dict)
    
    # Add tags if provided
    if tag_ids:
        tag_result = await db.execute(select(Tag).where(Tag.id.in_(tag_ids)))
        tags = tag_result.scalars().all()
        db_post.tags = tags
    
    db.add(db_post)
    await db.commit()
    await db.refresh(db_post)
    
    return db_post


async def update_post(db: AsyncSession, post_id: UUID, post_in: PostUpdate) -> Optional[Post]:
    """Update a post"""
    db_post = await get_post_by_id(db, post_id)
    if not db_post:
        return None
    
    update_data = post_in.model_dump(exclude_unset=True)
    
    # Update published_at if status changes to published
    if update_data.get('status') == 'published' and db_post.status != 'published':
        update_data['published_at'] = datetime.utcnow()
    
    for field, value in update_data.items():
        setattr(db_post, field, value)
    
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
    """Search posts by title or content"""
    search_query = select(Post).options(
        selectinload(Post.author),
        selectinload(Post.category),
        selectinload(Post.tags)
    ).where(
        or_(
            Post.title.ilike(f"%{query}%"),
            Post.content_markdown.ilike(f"%{query}%")
        )
    ).where(Post.status == 'published').limit(limit)
    
    result = await db.execute(search_query)
    return result.scalars().all()

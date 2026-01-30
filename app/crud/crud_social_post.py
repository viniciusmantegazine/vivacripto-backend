"""
CRUD operations for SocialPost model
"""
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import SocialPost


async def get_social_post_by_id(db: AsyncSession, social_post_id: UUID) -> Optional[SocialPost]:
    """Get a social post by ID"""
    result = await db.execute(
        select(SocialPost)
        .options(selectinload(SocialPost.post))
        .where(SocialPost.id == social_post_id)
    )
    return result.scalar_one_or_none()


async def get_social_posts_by_post_id(db: AsyncSession, post_id: UUID) -> List[SocialPost]:
    """Get all social posts for a specific post"""
    result = await db.execute(
        select(SocialPost)
        .where(SocialPost.post_id == post_id)
        .order_by(SocialPost.created_at.desc())
    )
    return list(result.scalars().all())


async def get_social_posts_by_platform(
    db: AsyncSession,
    platform: str,
    status: Optional[str] = None,
    limit: int = 100,
) -> List[SocialPost]:
    """Get social posts filtered by platform and optionally status"""
    query = select(SocialPost).where(SocialPost.platform == platform)

    if status:
        query = query.where(SocialPost.status == status)

    query = query.order_by(SocialPost.created_at.desc()).limit(limit)

    result = await db.execute(query)
    return list(result.scalars().all())


async def create_social_post(
    db: AsyncSession,
    post_id: UUID,
    platform: str,
    platform_post_id: Optional[str] = None,
    platform_url: Optional[str] = None,
    status: str = "pending",
    error_message: Optional[str] = None,
    auto_commit: bool = True,
) -> SocialPost:
    """
    Create a new social post record.

    Args:
        db: Database session
        post_id: ID of the related Post
        platform: Social media platform ('twitter', 'instagram', 'linkedin')
        platform_post_id: ID of the post on the social platform
        platform_url: URL of the post on the social platform
        status: Status of the publication ('pending', 'success', 'failed')
        error_message: Error message if publication failed
        auto_commit: If True, commits transaction automatically

    Returns:
        Created SocialPost instance
    """
    db_social_post = SocialPost(
        post_id=post_id,
        platform=platform,
        platform_post_id=platform_post_id,
        platform_url=platform_url,
        status=status,
        error_message=error_message,
        published_at=datetime.utcnow() if status == "success" else None,
    )

    db.add(db_social_post)

    if auto_commit:
        await db.commit()
        await db.refresh(db_social_post)

    return db_social_post


async def update_social_post_status(
    db: AsyncSession,
    social_post_id: UUID,
    status: str,
    platform_post_id: Optional[str] = None,
    platform_url: Optional[str] = None,
    error_message: Optional[str] = None,
    auto_commit: bool = True,
) -> Optional[SocialPost]:
    """
    Update the status of a social post.

    Args:
        db: Database session
        social_post_id: ID of the SocialPost to update
        status: New status ('pending', 'success', 'failed')
        platform_post_id: ID of the post on the social platform
        platform_url: URL of the post on the social platform
        error_message: Error message if publication failed
        auto_commit: If True, commits transaction automatically

    Returns:
        Updated SocialPost instance or None if not found
    """
    db_social_post = await get_social_post_by_id(db, social_post_id)
    if not db_social_post:
        return None

    db_social_post.status = status

    if platform_post_id is not None:
        db_social_post.platform_post_id = platform_post_id
    if platform_url is not None:
        db_social_post.platform_url = platform_url
    if error_message is not None:
        db_social_post.error_message = error_message
    if status == "success":
        db_social_post.published_at = datetime.utcnow()

    if auto_commit:
        await db.commit()
        await db.refresh(db_social_post)

    return db_social_post


async def delete_social_post(db: AsyncSession, social_post_id: UUID) -> bool:
    """Delete a social post record"""
    db_social_post = await get_social_post_by_id(db, social_post_id)
    if not db_social_post:
        return False

    await db.delete(db_social_post)
    await db.commit()

    return True


class CRUDSocialPost:
    """CRUD operations class for SocialPost"""

    async def get_by_id(self, db: AsyncSession, social_post_id: UUID) -> Optional[SocialPost]:
        return await get_social_post_by_id(db, social_post_id)

    async def get_by_post_id(self, db: AsyncSession, post_id: UUID) -> List[SocialPost]:
        return await get_social_posts_by_post_id(db, post_id)

    async def get_by_platform(
        self,
        db: AsyncSession,
        platform: str,
        status: Optional[str] = None,
        limit: int = 100,
    ) -> List[SocialPost]:
        return await get_social_posts_by_platform(db, platform, status, limit)

    async def create(
        self,
        db: AsyncSession,
        post_id: UUID,
        platform: str,
        platform_post_id: Optional[str] = None,
        platform_url: Optional[str] = None,
        status: str = "pending",
        error_message: Optional[str] = None,
        auto_commit: bool = True,
    ) -> SocialPost:
        return await create_social_post(
            db=db,
            post_id=post_id,
            platform=platform,
            platform_post_id=platform_post_id,
            platform_url=platform_url,
            status=status,
            error_message=error_message,
            auto_commit=auto_commit,
        )

    async def update_status(
        self,
        db: AsyncSession,
        social_post_id: UUID,
        status: str,
        platform_post_id: Optional[str] = None,
        platform_url: Optional[str] = None,
        error_message: Optional[str] = None,
        auto_commit: bool = True,
    ) -> Optional[SocialPost]:
        return await update_social_post_status(
            db=db,
            social_post_id=social_post_id,
            status=status,
            platform_post_id=platform_post_id,
            platform_url=platform_url,
            error_message=error_message,
            auto_commit=auto_commit,
        )

    async def delete(self, db: AsyncSession, social_post_id: UUID) -> bool:
        return await delete_social_post(db, social_post_id)


# Instância global para ser importada
crud_social_post = CRUDSocialPost()

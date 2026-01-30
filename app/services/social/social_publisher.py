"""
Social media publisher orchestrator.
Coordinates publishing to all enabled social media platforms.
"""
from typing import Optional
from dataclasses import dataclass, field
from uuid import UUID

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models import Post
from app.services.social.content_formatter import SocialContentFormatter
from app.services.social.twitter_adapter import TwitterAdapter, TwitterPublishResult


@dataclass
class SocialPublishResult:
    """Result of social media publishing"""
    twitter: Optional[TwitterPublishResult] = None
    instagram: Optional[dict] = None  # Future: InstagramPublishResult
    errors: list = field(default_factory=list)

    @property
    def has_any_success(self) -> bool:
        """Returns True if at least one platform succeeded"""
        if self.twitter and self.twitter.success:
            return True
        if self.instagram and self.instagram.get("success"):
            return True
        return False


class SocialPublisher:
    """
    Orchestrates publishing to social media platforms.

    Usage:
        publisher = SocialPublisher()
        result = await publisher.publish(post, db)
    """

    def __init__(self):
        self.formatter = SocialContentFormatter()
        self.twitter = TwitterAdapter() if settings.TWITTER_ENABLED else None
        # Future: self.instagram = InstagramAdapter() if settings.INSTAGRAM_ENABLED else None

    async def publish(
        self,
        post: Post,
        db: AsyncSession,
    ) -> SocialPublishResult:
        """
        Publishes post to all enabled social media platforms.

        Args:
            post: The Post object to publish
            db: Database session for saving social post records

        Returns:
            SocialPublishResult with results from each platform
        """
        result = SocialPublishResult()

        if not settings.SOCIAL_PUBLISHING_ENABLED:
            logger.debug("Social publishing is disabled")
            return result

        # Get category slug for hashtags
        category_slug = None
        if post.category:
            category_slug = post.category.slug

        # Publish to Twitter
        if self.twitter and settings.TWITTER_ENABLED:
            twitter_result = await self._publish_to_twitter(
                post=post,
                category_slug=category_slug,
                db=db,
            )
            result.twitter = twitter_result

        # Future: Publish to Instagram
        # if self.instagram and settings.INSTAGRAM_ENABLED:
        #     instagram_result = await self._publish_to_instagram(...)
        #     result.instagram = instagram_result

        return result

    async def _publish_to_twitter(
        self,
        post: Post,
        category_slug: Optional[str],
        db: AsyncSession,
    ) -> TwitterPublishResult:
        """Publishes to Twitter and saves result to database"""
        from app.crud.crud_social_post import crud_social_post

        try:
            # Format content for Twitter
            formatted = self.formatter.format_for_twitter(
                title=post.title,
                slug=post.slug,
                category_slug=category_slug,
            )

            # Publish tweet
            twitter_result = await self.twitter.publish(
                text=formatted.text,
                image_url=post.featured_image_url,
            )

            # Save to database
            await crud_social_post.create(
                db=db,
                post_id=post.id,
                platform="twitter",
                platform_post_id=twitter_result.tweet_id,
                platform_url=twitter_result.tweet_url,
                status="success" if twitter_result.success else "failed",
                error_message=twitter_result.error_message,
            )

            if twitter_result.success:
                logger.info(
                    f"Tweet publicado para post '{post.title[:50]}': {twitter_result.tweet_url}"
                )
            else:
                logger.warning(
                    f"Falha ao publicar tweet para post '{post.title[:50]}': {twitter_result.error_message}"
                )

            return twitter_result

        except Exception as e:
            error_message = str(e)
            logger.error(f"Erro ao publicar no Twitter: {error_message}")

            # Save error to database
            try:
                await crud_social_post.create(
                    db=db,
                    post_id=post.id,
                    platform="twitter",
                    platform_post_id=None,
                    platform_url=None,
                    status="failed",
                    error_message=error_message,
                )
            except Exception as db_error:
                logger.error(f"Erro ao salvar falha no banco: {db_error}")

            return TwitterPublishResult(
                success=False,
                error_message=error_message,
            )

    async def publish_single_platform(
        self,
        post: Post,
        platform: str,
        db: AsyncSession,
    ) -> dict:
        """
        Publishes to a single platform.

        Args:
            post: The Post object to publish
            platform: Platform name ('twitter' or 'instagram')
            db: Database session

        Returns:
            Dict with success status and details
        """
        category_slug = post.category.slug if post.category else None

        if platform == "twitter":
            if not self.twitter:
                return {"success": False, "error": "Twitter not configured"}
            result = await self._publish_to_twitter(post, category_slug, db)
            return {
                "success": result.success,
                "url": result.tweet_url,
                "error": result.error_message,
            }

        # Future: Instagram
        # if platform == "instagram":
        #     ...

        return {"success": False, "error": f"Unknown platform: {platform}"}

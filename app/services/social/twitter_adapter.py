"""
Twitter/X API adapter for publishing tweets.
Uses Tweepy library for Twitter API v2 integration.
"""
import asyncio
from typing import Optional
from dataclasses import dataclass

import httpx
from loguru import logger

from app.core.config import settings


@dataclass
class TwitterPublishResult:
    """Result of a Twitter publish operation"""
    success: bool
    tweet_id: Optional[str] = None
    tweet_url: Optional[str] = None
    error_message: Optional[str] = None


class TwitterAdapter:
    """Adapter for Twitter/X API v2"""

    TWITTER_USERNAME = "vivacripto"  # Update with actual username

    def __init__(self):
        self._client = None
        self._api = None

    def _get_client(self):
        """Lazy initialization of Tweepy client"""
        if self._client is None:
            try:
                import tweepy

                self._client = tweepy.Client(
                    consumer_key=settings.TWITTER_API_KEY,
                    consumer_secret=settings.TWITTER_API_SECRET,
                    access_token=settings.TWITTER_ACCESS_TOKEN,
                    access_token_secret=settings.TWITTER_ACCESS_SECRET,
                )

                # API v1.1 for media upload (v2 doesn't support media upload yet)
                auth = tweepy.OAuth1UserHandler(
                    settings.TWITTER_API_KEY,
                    settings.TWITTER_API_SECRET,
                    settings.TWITTER_ACCESS_TOKEN,
                    settings.TWITTER_ACCESS_SECRET,
                )
                self._api = tweepy.API(auth)

            except ImportError:
                logger.error("Tweepy not installed. Run: pip install tweepy")
                raise
            except Exception as e:
                logger.error(f"Failed to initialize Twitter client: {e}")
                raise

        return self._client, self._api

    async def publish(
        self,
        text: str,
        image_url: Optional[str] = None,
    ) -> TwitterPublishResult:
        """
        Publishes a tweet with optional image.

        Args:
            text: Tweet text (max 280 characters)
            image_url: Optional URL of image to attach

        Returns:
            TwitterPublishResult with success status and tweet details
        """
        try:
            client, api = self._get_client()

            media_ids = None
            if image_url:
                media_id = await self._upload_media(api, image_url)
                if media_id:
                    media_ids = [media_id]

            # Create tweet (run in thread pool since tweepy is sync)
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: client.create_tweet(text=text, media_ids=media_ids)
            )

            tweet_id = response.data["id"]
            tweet_url = f"https://twitter.com/{self.TWITTER_USERNAME}/status/{tweet_id}"

            logger.info(f"Tweet publicado com sucesso: {tweet_url}")

            return TwitterPublishResult(
                success=True,
                tweet_id=tweet_id,
                tweet_url=tweet_url,
            )

        except Exception as e:
            error_message = str(e)
            logger.error(f"Erro ao publicar tweet: {error_message}")

            return TwitterPublishResult(
                success=False,
                error_message=error_message,
            )

    async def _upload_media(
        self,
        api,
        image_url: str,
    ) -> Optional[str]:
        """
        Downloads image from URL and uploads to Twitter.

        Twitter API v1.1 is required for media upload.
        Returns media_id if successful.
        """
        try:
            # Download image
            async with httpx.AsyncClient() as client:
                response = await client.get(image_url, timeout=30.0)
                response.raise_for_status()
                image_data = response.content

            # Upload to Twitter (sync operation)
            loop = asyncio.get_event_loop()
            media = await loop.run_in_executor(
                None,
                lambda: api.media_upload(
                    filename="image.jpg",
                    file=image_data,
                )
            )

            logger.debug(f"Media uploaded to Twitter: {media.media_id}")
            return str(media.media_id)

        except Exception as e:
            logger.warning(f"Falha ao fazer upload de mídia para Twitter: {e}")
            return None

    def is_configured(self) -> bool:
        """Checks if Twitter credentials are configured"""
        return all([
            settings.TWITTER_API_KEY,
            settings.TWITTER_API_SECRET,
            settings.TWITTER_ACCESS_TOKEN,
            settings.TWITTER_ACCESS_SECRET,
        ])

"""
Content formatter for social media posts.
Formats content for different social media platforms with appropriate length and hashtags.
"""
from typing import List, Optional
from dataclasses import dataclass

from app.core.config import settings


@dataclass
class FormattedContent:
    """Formatted content for social media"""
    text: str
    hashtags: List[str]
    url: Optional[str] = None


class SocialContentFormatter:
    """Formats content for different social media platforms"""

    CATEGORY_HASHTAGS = {
        "bitcoin": ["Bitcoin", "BTC", "Crypto"],
        "ethereum": ["Ethereum", "ETH", "Crypto", "DeFi"],
        "altcoins": ["Altcoins", "Crypto", "Criptomoedas"],
        "defi": ["DeFi", "Crypto", "FinançasDescentralizadas"],
        "regulação": ["CryptoRegulação", "Crypto", "Regulamentação"],
        "regulacao": ["CryptoRegulação", "Crypto", "Regulamentação"],
        "airdrop": ["Airdrop", "Crypto", "FreeCrypto"],
    }

    BASE_HASHTAGS = ["VivaCripto", "Criptomoedas"]

    TWITTER_MAX_LENGTH = 280
    TWITTER_URL_LENGTH = 23  # Twitter encurta URLs para 23 caracteres

    INSTAGRAM_MAX_LENGTH = 2200

    def format_for_twitter(
        self,
        title: str,
        slug: str,
        category_slug: Optional[str] = None,
    ) -> FormattedContent:
        """
        Formats content for Twitter/X.

        Twitter has a 280 character limit. URLs count as 23 characters.
        Format: {title} {hashtags} {url}
        """
        url = f"{settings.FRONTEND_URL}/{slug}"
        hashtags = self._get_hashtags(category_slug, limit=3)
        hashtags_text = " ".join(f"#{tag}" for tag in hashtags)

        # Calculate available space for title
        # URL (23) + space (1) + hashtags + space (1)
        reserved_space = self.TWITTER_URL_LENGTH + 2 + len(hashtags_text)
        max_title_length = self.TWITTER_MAX_LENGTH - reserved_space

        # Truncate title if needed
        truncated_title = self._truncate_text(title, max_title_length)

        text = f"{truncated_title}\n\n{hashtags_text}\n\n{url}"

        return FormattedContent(
            text=text,
            hashtags=hashtags,
            url=url,
        )

    def format_for_instagram(
        self,
        title: str,
        excerpt: str,
        category_slug: Optional[str] = None,
    ) -> FormattedContent:
        """
        Formats content for Instagram.

        Instagram allows up to 2200 characters.
        Format: {title}\n\n{excerpt}\n\n{hashtags}\n\n{cta}
        """
        hashtags = self._get_hashtags(category_slug, limit=10)
        hashtags_text = " ".join(f"#{tag}" for tag in hashtags)

        cta = "🔗 Link na bio para ler a notícia completa!"

        # Build the caption
        parts = [
            f"📰 {title}",
            "",
            excerpt,
            "",
            hashtags_text,
            "",
            cta,
        ]

        text = "\n".join(parts)

        # Truncate if exceeds limit
        if len(text) > self.INSTAGRAM_MAX_LENGTH:
            available_for_excerpt = (
                self.INSTAGRAM_MAX_LENGTH
                - len(title) - len(hashtags_text) - len(cta) - 20  # margins
            )
            truncated_excerpt = self._truncate_text(excerpt, available_for_excerpt)
            parts[2] = truncated_excerpt
            text = "\n".join(parts)

        return FormattedContent(
            text=text,
            hashtags=hashtags,
            url=None,  # Instagram doesn't allow clickable links in captions
        )

    def _get_hashtags(
        self,
        category_slug: Optional[str] = None,
        limit: int = 5,
    ) -> List[str]:
        """Gets relevant hashtags based on category"""
        hashtags = list(self.BASE_HASHTAGS)

        if category_slug:
            category_key = category_slug.lower()
            category_tags = self.CATEGORY_HASHTAGS.get(category_key, [])
            hashtags.extend(category_tags)

        # Remove duplicates while preserving order
        seen = set()
        unique_hashtags = []
        for tag in hashtags:
            if tag.lower() not in seen:
                seen.add(tag.lower())
                unique_hashtags.append(tag)

        return unique_hashtags[:limit]

    def _truncate_text(self, text: str, max_length: int) -> str:
        """Truncates text to max_length, adding ellipsis if truncated"""
        if len(text) <= max_length:
            return text

        # Truncate and add ellipsis
        truncated = text[:max_length - 3].rsplit(" ", 1)[0]
        return f"{truncated}..."

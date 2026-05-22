"""
Airdrop Post Generator

Orquestra: WebResearcher → Claude Sonnet 4.6 (com fallback Gemini)
→ artigo dict pronto pra publicação.
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Dict, Optional

from loguru import logger
from slugify import slugify

from app.core.config import settings
from app.services.ai.prompts.airdrop_prompts import (
    AIRDROP_SYSTEM_PROMPT,
    build_airdrop_user_prompt,
)
from app.services.airdrop.web_researcher import ResearchResult, WebResearcher

try:
    from anthropic import AsyncAnthropic

    ANTHROPIC_AVAILABLE = True
except ImportError:  # pragma: no cover
    ANTHROPIC_AVAILABLE = False
    logger.warning("Anthropic SDK não instalado. Airdrop generator vai depender só do Gemini.")


class AirdropPostGenerator:
    """Gera posts sobre airdrops a partir de pesquisa web + Claude."""

    CLAUDE_MODEL = "claude-sonnet-4-6"
    MAX_TOKENS = 3000
    TEMPERATURE = 0.5

    def __init__(self):
        self.web_researcher = WebResearcher()

        self.claude_client = None
        self.claude_available = False
        self._init_claude()

        # fallback (lazy)
        self._content_generator = None
        # lazy image generator
        self._image_generator = None

    def _init_claude(self) -> None:
        if not ANTHROPIC_AVAILABLE:
            return
        if not settings.ANTHROPIC_API_KEY:
            logger.warning("AirdropPostGenerator: ANTHROPIC_API_KEY ausente")
            return
        try:
            self.claude_client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
            self.claude_available = True
            logger.info(f"AirdropPostGenerator: Claude pronto ({self.CLAUDE_MODEL})")
        except Exception as e:
            logger.error(f"AirdropPostGenerator: falha ao iniciar Claude: {e}")

    @property
    def content_generator(self):
        """Fallback Gemini (lazy)."""
        if self._content_generator is None:
            from app.services.ai.content_generator import ContentGenerator

            self._content_generator = ContentGenerator()
        return self._content_generator

    @content_generator.setter
    def content_generator(self, value):
        self._content_generator = value

    @property
    def image_generator(self):
        if self._image_generator is None:
            from app.services.ai.image_generator import ImageGenerator

            self._image_generator = ImageGenerator()
        return self._image_generator

    async def generate(
        self,
        project_name: str,
        official_url: str,
        referral_url: str,
    ) -> Optional[Dict]:
        """
        Roda o fluxo completo: pesquisa → IA → article dict.

        Returns:
            Dict no shape esperado por ArticlePublisher.publish_article, com
            campos extras `sources_used` e `word_count`, ou None em falha.
        """
        research = await self.web_researcher.gather_context(project_name, official_url)

        user_prompt = build_airdrop_user_prompt(
            project_name=project_name,
            official_url=official_url,
            referral_url=referral_url,
            sources_text=research.sources_text,
            current_date=datetime.utcnow().strftime("%Y-%m-%d"),
        )

        article = await self._generate_with_claude(user_prompt)

        if article is None:
            logger.error("AirdropPostGenerator: Claude não retornou artigo válido")
            return None

        # garante slug
        if not article.get("slug"):
            article["slug"] = slugify(article.get("title", project_name))

        # gera imagem (não-bloqueante)
        article["image_url"] = await self._generate_image(article)

        article["sources_used"] = research.sources_used
        article["word_count"] = len(article.get("content_markdown", "").split())
        return article

    async def _generate_with_claude(self, user_prompt: str) -> Optional[Dict]:
        """Chama Claude e parsa o JSON de saída. Retorna None em falha."""
        if not self.claude_available or self.claude_client is None:
            return None
        try:
            response = await self.claude_client.messages.create(
                model=self.CLAUDE_MODEL,
                max_tokens=self.MAX_TOKENS,
                temperature=self.TEMPERATURE,
                system=AIRDROP_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_prompt}],
            )
            text = response.content[0].text
            return self._parse_json(text)
        except Exception as e:
            logger.error(f"AirdropPostGenerator: Claude falhou: {e}")
            return None

    def _parse_json(self, text: str) -> Optional[Dict]:
        """Tenta parsear JSON, removendo cercas ``` se presentes."""
        cleaned = text.strip()
        if cleaned.startswith("```"):
            # remove cercas estilo ```json ... ```
            cleaned = cleaned.split("```", 2)[1]
            if cleaned.startswith("json"):
                cleaned = cleaned[4:]
            cleaned = cleaned.rsplit("```", 1)[0]
        try:
            data = json.loads(cleaned.strip())
            required = {"title", "content_markdown"}
            if not required.issubset(data.keys()):
                logger.error(f"AirdropPostGenerator: JSON sem campos obrigatórios: {data.keys()}")
                return None
            return data
        except json.JSONDecodeError as e:
            logger.error(f"AirdropPostGenerator: JSON inválido: {e}")
            return None

    async def _generate_image(self, article: Dict) -> Optional[str]:
        """Gera imagem, retorna None em falha (não bloqueia)."""
        try:
            return await self.image_generator.generate_and_upload_image(
                article["title"],
                article["content_markdown"],
                category_name="airdrop",
            )
        except Exception as e:
            logger.warning(f"AirdropPostGenerator: imagem falhou: {e}")
            return None

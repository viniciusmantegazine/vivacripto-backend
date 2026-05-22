"""
Airdrop Post Generator

Orquestra: WebResearcher → Claude Sonnet 4.6 (com fallback Gemini)
→ artigo dict pronto pra publicação.
"""
from __future__ import annotations

import json
import re
import unicodedata
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
        generate_image: bool = True,
    ) -> Optional[Dict]:
        """
        Roda o fluxo completo: pesquisa → IA → validação extra → article dict.

        Args:
            generate_image: Se False, pula a geração de imagem (útil em
                preview pra não desperdiçar chamadas Cloudinary/Gemini-img
                em conteúdo que pode ser descartado).
        """
        research = await self.web_researcher.gather_context(project_name, official_url)

        article = await self._generate_validated(
            project_name=project_name,
            official_url=official_url,
            referral_url=referral_url,
            research=research,
        )
        if article is None:
            return None

        if not article.get("slug"):
            article["slug"] = slugify(article.get("title", project_name))

        article["image_url"] = (
            await self._generate_image(article) if generate_image else None
        )
        article["sources_used"] = research.sources_used
        article["word_count"] = len(article.get("content_markdown", "").split())
        return article

    async def _generate_validated(
        self,
        project_name: str,
        official_url: str,
        referral_url: str,
        research: ResearchResult,
        correction_hint: Optional[str] = None,
    ) -> Optional[Dict]:
        """
        Gera com Claude (fallback Gemini), valida link de referência/oficial.
        Se falhar a validação, regenera UMA vez com hint de correção.
        Retorna None se ainda falhar.
        """
        user_prompt = build_airdrop_user_prompt(
            project_name=project_name,
            official_url=official_url,
            referral_url=referral_url,
            sources_text=research.sources_text,
            current_date=datetime.utcnow().strftime("%Y-%m-%d"),
        )
        if correction_hint:
            user_prompt += f"\n\nINSTRUÇÃO DE CORREÇÃO:\n{correction_hint}"

        article = await self._generate_with_claude(user_prompt)
        if article is None:
            logger.warning("AirdropPostGenerator: Claude falhou, tentando Gemini")
            article = await self._generate_with_gemini(user_prompt)
        if article is None:
            return None

        errors = self._post_validate(article, referral_url, official_url)
        if not errors:
            return article

        # Regenera UMA vez
        if correction_hint is not None:
            logger.error(f"AirdropPostGenerator: validação falhou após retry: {errors}")
            return None

        hint = (
            "A geração anterior tinha estes problemas: "
            + "; ".join(errors)
            + ". Corrija no novo JSON."
        )
        logger.warning(f"AirdropPostGenerator: regenerando uma vez ({errors})")
        return await self._generate_validated(
            project_name=project_name,
            official_url=official_url,
            referral_url=referral_url,
            research=research,
            correction_hint=hint,
        )

    @staticmethod
    def _strip_accents(text: str) -> str:
        """Remove acentos via NFKD, retorna lowercase ASCII."""
        normalized = unicodedata.normalize("NFKD", text)
        ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
        return ascii_text.lower()

    @staticmethod
    def _url_appears_in_markdown(url: str, content: str) -> bool:
        """
        Verifica se a URL aparece no markdown, tolerando:
        - trailing slash divergente
        - query string adicional (?utm=...)
        - markdown link com title attribute
        - fragments
        Estratégia: extrai todas as URLs de links markdown [text](url) +
        links autolink, normaliza, compara base.
        """
        target = url.rstrip("/").split("?")[0].split("#")[0]
        # Char class de URL: exclui whitespace e delimitadores comuns de
        # markdown (`)`, `]`, `>`, `"`) que NÃO podem aparecer em URLs válidas.
        link_re = re.compile(
            r'\]\(\s*([^)\s]+)'           # markdown link: ](url)
            r'|<(https?://[^>\s]+)>'      # autolink: <url>
            r'|(https?://[^\s)\]>"]+)'    # URL crua
        )
        for match in link_re.finditer(content):
            for raw in filter(None, match.groups()):
                candidate = raw.rstrip('.,;').rstrip("/").split("?")[0].split("#")[0]
                if candidate == target:
                    return True
        return False

    def _post_validate(
        self,
        article: Dict,
        referral_url: str,
        official_url: str,
    ) -> list:
        """
        Verifica:
        - referral_url está presente no markdown (match tolerante)
        - official_url está presente no markdown (match tolerante)
        - frase-chave do disclosure presente (Unicode-normalized)
        Retorna lista de erros (vazia se ok).
        """
        errors = []
        content = article.get("content_markdown", "")
        if not self._url_appears_in_markdown(referral_url, content):
            errors.append(f"link de referência ({referral_url}) ausente no conteúdo")
        if not self._url_appears_in_markdown(official_url, content):
            errors.append(f"link oficial ({official_url}) ausente no bloco de disclosure")
        normalized = self._strip_accents(content)
        if "nao constitui recomendacao" not in normalized:
            errors.append("frase 'não constitui recomendação' ausente no disclosure")
        return errors

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

    async def _generate_with_gemini(self, user_prompt: str) -> Optional[Dict]:
        """
        Fallback usando google-genai (Gemini Flash).

        Reaproveita o client já configurado no ContentGenerator existente.
        Se algo der errado, retorna None.
        """
        try:
            cg = self.content_generator  # lazy import
            if cg is None:
                return None
            client = getattr(cg, "gemini_client", None)
            if client is None:
                logger.warning("AirdropPostGenerator: ContentGenerator sem client Gemini")
                return None

            # Gemini usa um prompt único (concatena system + user)
            combined = AIRDROP_SYSTEM_PROMPT + "\n\n---\n\n" + user_prompt

            response = await client.aio.models.generate_content(
                model="gemini-2.5-flash",
                contents=combined,
            )
            text = getattr(response, "text", None)
            if not text:
                return None
            return self._parse_json(text)
        except Exception as e:
            logger.error(f"AirdropPostGenerator: Gemini fallback falhou: {e}")
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

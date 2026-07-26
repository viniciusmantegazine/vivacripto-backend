"""
Article Extractor Service
Busca o HTML da notícia original e extrai o texto completo com trafilatura.

Motivação: o `summary` de RSS costuma ter 1-2 frases — insuficiente para o
ContentGenerator produzir 700+ palavras sem alucinar. Com o texto completo,
a geração fica ancorada em fatos reais da matéria original.

Qualquer falha (rede, paywall, extração vazia) retorna None e o pipeline
segue apenas com o resumo do RSS — este serviço nunca bloqueia o fluxo.
"""
import asyncio
from typing import Optional

import httpx
from loguru import logger

try:
    import trafilatura
    TRAFILATURA_AVAILABLE = True
except ImportError:
    TRAFILATURA_AVAILABLE = False
    logger.warning(
        "trafilatura não instalado — geração usará apenas o resumo do RSS"
    )

# Extração abaixo disso = falhou (página de erro, paywall, consent wall)
MIN_TEXT_CHARS = 200
# Teto para limitar o tamanho do prompt de geração
MAX_TEXT_CHARS = 8000

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
    ),
}


class ArticleExtractor:
    """Extrai o texto completo de uma página de notícia."""

    def __init__(self, timeout: int = 10):
        self.timeout = timeout

    async def extract(self, url: str) -> Optional[str]:
        """
        Busca a página e extrai o texto principal.

        Args:
            url: URL da notícia original

        Returns:
            Texto extraído (até MAX_TEXT_CHARS) ou None em qualquer falha
        """
        if not url or not TRAFILATURA_AVAILABLE:
            return None

        html = await self._fetch(url)
        if not html:
            return None

        # trafilatura.extract é síncrono e CPU-bound: fora do event loop
        text = await asyncio.to_thread(
            trafilatura.extract,
            html,
            include_comments=False,
            include_tables=False,
        )

        if not text:
            logger.warning(f"Extração de texto vazia para {url}")
            return None

        text = text.strip()
        if len(text) < MIN_TEXT_CHARS:
            logger.warning(
                f"Extração muito curta ({len(text)} chars) para {url} — descartada"
            )
            return None

        return text[:MAX_TEXT_CHARS]

    async def _fetch(self, url: str) -> Optional[str]:
        """Busca o HTML da página. Falha => None (nunca levanta exceção)."""
        try:
            async with httpx.AsyncClient(
                timeout=self.timeout,
                follow_redirects=True,
                headers=HEADERS,
            ) as client:
                response = await client.get(url)
                response.raise_for_status()
                return response.text
        except Exception as e:
            logger.warning(
                f"Falha ao buscar página da notícia {url}: {type(e).__name__}: {e}"
            )
            return None

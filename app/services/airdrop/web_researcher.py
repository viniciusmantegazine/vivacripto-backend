"""
Web Researcher para Airdrop Post Generator.

Coleta contexto público sobre um projeto cripto a partir de:
- 3 buscas no DuckDuckGo (via ddgs)
- Fetch HTTP das URLs ranqueadas
- Página oficial fornecida no request (sempre incluída)

Aplica blocklist (social/vídeo), whitelist boost (fontes cripto conhecidas)
e trunca conteúdo extraído por fonte.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Tuple
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup
from loguru import logger


BLOCKED_DOMAINS = {
    "reddit.com", "twitter.com", "x.com",
    "youtube.com", "tiktok.com",
    "telegram.org", "discord.com",
}

PREFERRED_DOMAINS = {
    "coinmarketcap.com", "coingecko.com", "cryptorank.io",
    "coindesk.com", "cointelegraph.com", "decrypt.co",
    "theblock.co", "cryptoslate.com", "messari.io",
    "airdrops.io", "coinlist.co",
}

# Quanto subtraímos do rank pra cada domínio whitelisted (ranks menores = melhores)
WHITELIST_BOOST = 100

# Limite de caracteres extraídos por URL
SOURCE_TRUNCATE_CHARS = 3000

# Top-N URLs efetivamente consultadas (DDG + oficial)
TOP_N_URLS = 5


class ResearchFailedError(Exception):
    """Levantada quando não há nenhuma fonte primária disponível."""


@dataclass
class ResearchResult:
    sources_text: str
    sources_used: List[str] = field(default_factory=list)


class WebResearcher:
    """Coleta contexto web sobre um projeto cripto."""

    def _domain_of(self, url: str) -> str:
        try:
            return urlparse(url).netloc.lower().lstrip("www.")
        except Exception:
            return ""

    def _dedup_by_domain(
        self, candidates: List[Tuple[str, int]]
    ) -> List[Tuple[str, int]]:
        """
        Recebe lista de (url, rank). Mantém apenas a melhor URL (menor rank)
        por domínio. Preserva a ordem original (estável).
        """
        seen: dict[str, Tuple[str, int]] = {}
        for url, rank in candidates:
            domain = self._domain_of(url)
            if not domain:
                continue
            if domain not in seen or rank < seen[domain][1]:
                seen[domain] = (url, rank)
        # ordena por rank ascendente
        return sorted(seen.values(), key=lambda t: t[1])

    def _apply_blocklist(
        self, candidates: List[Tuple[str, int]]
    ) -> List[Tuple[str, int]]:
        """Remove URLs cujo domínio (ou sufixo) esteja na BLOCKED_DOMAINS."""
        result = []
        for url, rank in candidates:
            domain = self._domain_of(url)
            blocked = any(
                domain == bd or domain.endswith("." + bd) for bd in BLOCKED_DOMAINS
            )
            if not blocked:
                result.append((url, rank))
        return result

    def _apply_whitelist_boost(
        self, candidates: List[Tuple[str, int]]
    ) -> List[Tuple[str, int]]:
        """
        Para cada URL cujo domínio está em PREFERRED_DOMAINS, subtrai WHITELIST_BOOST
        do rank (ranks menores ganham prioridade na ordenação).
        """
        result = []
        for url, rank in candidates:
            domain = self._domain_of(url)
            is_preferred = any(
                domain == pd or domain.endswith("." + pd) for pd in PREFERRED_DOMAINS
            )
            new_rank = rank - WHITELIST_BOOST if is_preferred else rank
            result.append((url, new_rank))
        return sorted(result, key=lambda t: t[1])

    def _select_top(
        self,
        ranked: List[Tuple[str, int]],
        official_url: str,
        top_n: int = TOP_N_URLS,
    ) -> List[str]:
        """
        Seleciona as top-N URLs. Sempre inclui a official_url (sem duplicar).
        """
        urls = [u for u, _ in ranked]
        # Garante que official_url está incluída como primeira (mas sem duplicar)
        if official_url in urls:
            urls.remove(official_url)
        selected = [official_url] + urls[: max(0, top_n - 1)]
        return selected[:top_n]

    def _extract_text(self, html: str) -> str:
        """
        Extrai texto limpo do HTML.
        - Remove <script>, <style>, <nav>, <footer>, <header>, <aside>
        - Normaliza whitespace
        - Trunca a SOURCE_TRUNCATE_CHARS
        """
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
            tag.decompose()
        text = soup.get_text(separator=" ", strip=True)
        # Normaliza múltiplos espaços
        text = " ".join(text.split())
        return text[:SOURCE_TRUNCATE_CHARS]

    async def _fetch_url(
        self, client: httpx.AsyncClient, url: str
    ) -> Optional[str]:
        """
        Fetch HTTP de uma URL. Retorna texto extraído ou None se:
        - Erro HTTP (timeout, 4xx, 5xx, conexão)
        - Content-Type não é HTML
        """
        try:
            response = await client.get(url, timeout=10.0, follow_redirects=True)
            if response.status_code != 200:
                logger.warning(f"WebResearcher: status {response.status_code} para {url}")
                return None
            content_type = response.headers.get("content-type", "").lower()
            if "html" not in content_type:
                logger.debug(f"WebResearcher: pulando {url} (content-type={content_type})")
                return None
            return self._extract_text(response.text)
        except Exception as e:
            logger.warning(f"WebResearcher: falha ao fetch {url}: {e}")
            return None

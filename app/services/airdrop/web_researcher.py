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

import asyncio
from dataclasses import dataclass, field
from typing import List, Optional, Tuple
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup
from loguru import logger

try:
    from ddgs import DDGS  # ddgs >= 7.0
except ImportError:  # pragma: no cover
    from duckduckgo_search import DDGS  # legacy fallback


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
            netloc = urlparse(url).netloc.lower()
            # Bug histórico: .lstrip("www.") remove qualquer um desses chars
            # à esquerda (ex: "wax.com" virava "x.com"). Usa removeprefix.
            return netloc.removeprefix("www.")
        except Exception:
            return ""

    def _normalize_url(self, url: str) -> str:
        """
        Normaliza URL pra comparação estável: lowercase scheme+host,
        remove trailing slash do path, descarta fragment.
        """
        try:
            p = urlparse(url)
            path = (p.path or "").rstrip("/")
            netloc = p.netloc.lower()
            scheme = p.scheme.lower() or "https"
            query = f"?{p.query}" if p.query else ""
            return f"{scheme}://{netloc}{path}{query}"
        except Exception:
            return url

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
        Comparação de duplicata é feita por URL normalizada (trailing slash,
        case do host) pra não duplicar variantes equivalentes.
        """
        official_norm = self._normalize_url(official_url)
        deduped: List[str] = []
        for url, _ in ranked:
            if self._normalize_url(url) != official_norm:
                deduped.append(url)
        selected = [official_url] + deduped[: max(0, top_n - 1)]
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

    # User-Agent realista — muitos sites bloqueiam default httpx
    FETCH_HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (compatible; VivaCriptoBot/1.0; "
            "+https://vivacripto.com.br/about)"
        ),
        "Accept": "text/html,application/xhtml+xml",
    }
    FETCH_TIMEOUT_SECONDS = 10.0

    async def _fetch_url(
        self, client: httpx.AsyncClient, url: str
    ) -> Optional[str]:
        """
        Fetch HTTP de uma URL. Retorna texto extraído ou None se:
        - Erro HTTP (timeout, 4xx, 5xx, conexão)
        - Content-Type não é HTML
        """
        try:
            response = await client.get(
                url,
                timeout=self.FETCH_TIMEOUT_SECONDS,
                follow_redirects=True,
                headers=self.FETCH_HEADERS,
            )
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

    DDG_RESULTS_PER_QUERY = 4

    def _build_queries(self, project_name: str) -> List[str]:
        return [
            f"{project_name} airdrop",
            f"{project_name} como participar",
            f"{project_name} token tokenomics",
        ]

    def _search_ddg(self, project_name: str) -> List[Tuple[str, int]]:
        """
        Executa as 3 buscas no DDG (síncrono via ddgs). Retorna lista de
        (url, rank) onde rank é a posição global (menor = melhor).
        """
        candidates: List[Tuple[str, int]] = []
        global_rank = 0
        try:
            with DDGS() as ddgs:
                for query in self._build_queries(project_name):
                    try:
                        results = list(
                            ddgs.text(query, max_results=self.DDG_RESULTS_PER_QUERY)
                        )
                    except Exception as e:
                        logger.warning(f"WebResearcher: DDG falhou para '{query}': {e}")
                        continue
                    for item in results:
                        url = item.get("href") or item.get("url") or ""
                        if url:
                            global_rank += 1
                            candidates.append((url, global_rank))
        except Exception as e:
            logger.warning(f"WebResearcher: erro ao iniciar DDGS: {e}")
        return candidates

    # Teto pra evitar request travado infinito (DDG + fetch paralelo)
    OVERALL_TIMEOUT_SECONDS = 45.0
    DDG_TIMEOUT_SECONDS = 15.0

    async def gather_context(
        self,
        project_name: str,
        official_url: str,
    ) -> ResearchResult:
        """
        Pesquisa, fetch e consolida texto sobre o projeto.

        Raises:
            ResearchFailedError: se a página oficial não pôde ser baixada
                e nenhuma fonte secundária foi obtida, ou se o tempo total
                excedeu OVERALL_TIMEOUT_SECONDS.
        """
        try:
            return await asyncio.wait_for(
                self._gather_context_inner(project_name, official_url),
                timeout=self.OVERALL_TIMEOUT_SECONDS,
            )
        except asyncio.TimeoutError:
            raise ResearchFailedError(
                f"Pesquisa excedeu {self.OVERALL_TIMEOUT_SECONDS}s para '{project_name}'"
            )

    async def _gather_context_inner(
        self,
        project_name: str,
        official_url: str,
    ) -> ResearchResult:
        # 1) busca DDG (síncrono — rodar em thread pra não bloquear loop)
        try:
            raw_candidates = await asyncio.wait_for(
                asyncio.to_thread(self._search_ddg, project_name),
                timeout=self.DDG_TIMEOUT_SECONDS,
            )
        except asyncio.TimeoutError:
            logger.warning(
                f"WebResearcher: DDG excedeu {self.DDG_TIMEOUT_SECONDS}s — "
                "seguindo só com URL oficial"
            )
            raw_candidates = []

        # 2) filtragem
        candidates = self._apply_blocklist(raw_candidates)
        candidates = self._dedup_by_domain(candidates)
        candidates = self._apply_whitelist_boost(candidates)

        # 3) seleção (oficial sempre incluída como FONTE 1)
        selected_urls = self._select_top(candidates, official_url, top_n=TOP_N_URLS)
        logger.info(f"WebResearcher: vai fetch {len(selected_urls)} URLs para '{project_name}'")

        # 4) fetch paralelo
        async with httpx.AsyncClient() as client:
            fetch_tasks = [self._fetch_url(client, url) for url in selected_urls]
            texts = await asyncio.gather(*fetch_tasks, return_exceptions=False)

        # 5) emparelhar urls x textos, descartar falhas
        official_norm = self._normalize_url(official_url)
        official_text: Optional[str] = None
        secondary_blocks: List[Tuple[str, str]] = []
        for url, text in zip(selected_urls, texts):
            if not text:
                continue
            if self._normalize_url(url) == official_norm:
                official_text = text
            else:
                secondary_blocks.append((url, text))

        # 6) regra dura: precisa de pelo menos a oficial OU 1 secundária
        if official_text is None and not secondary_blocks:
            raise ResearchFailedError(
                f"Não foi possível baixar nenhuma fonte para '{project_name}'"
            )

        # 7) montar bloco consolidado
        parts = [f'=== FONTES PESQUISADAS PARA "{project_name}" ===\n']
        sources_used: List[str] = []
        index = 1

        if official_text is not None:
            parts.append(f"[FONTE {index} - OFICIAL] {official_url}\n{official_text}\n")
            sources_used.append(official_url)
            index += 1
        else:
            logger.warning(
                f"WebResearcher: página oficial {official_url} indisponível, "
                "seguindo só com secundárias"
            )

        for url, text in secondary_blocks:
            parts.append(f"[FONTE {index}] {url}\n{text}\n")
            sources_used.append(url)
            index += 1

        parts.append("=== FIM DAS FONTES ===")
        return ResearchResult(
            sources_text="\n".join(parts),
            sources_used=sources_used,
        )

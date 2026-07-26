"""
RSS Feed Collector Service
Coleta notícias de feeds RSS de fontes confiáveis
"""
import feedparser
import httpx
import asyncio
import html as html_lib
import re
from typing import List, Dict, Optional
from datetime import datetime, timedelta, timezone
from loguru import logger


_TAG_RE = re.compile(r"<[^>]+>")


def _strip_html(text) -> str:
    """
    Remove tags HTML e entidades de texto vindo de feeds RSS.
    Vários feeds mandam `summary` com HTML embutido, que contaminaria o
    prompt do LLM e a comparação de similaridade do dedup de fontes.
    """
    if not text:
        return ""
    text = _TAG_RE.sub(" ", text)
    text = html_lib.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


class RSSCollector:
    """Coletor de notícias via RSS feeds"""
    
    RSS_FEEDS = [
        {
            "name": "CoinDesk",
            "url": "https://www.coindesk.com/arc/outboundfeeds/rss/",
            "language": "en"
        },
        {
            "name": "Cointelegraph",
            "url": "https://cointelegraph.com/rss",
            "language": "en"
        },
        {
            "name": "CryptoSlate",
            "url": "https://cryptoslate.com/feed/",
            "language": "en"
        },
        {
            "name": "Decrypt",
            "url": "https://decrypt.co/feed",
            "language": "en"
        },
        {
            "name": "Bitcoin Magazine",
            "url": "https://bitcoinmagazine.com/feed",
            "language": "en"
        },
    ]

    # Alguns feeds (CoinDesk, Bitcoin Magazine) retornam 403 para User-Agents
    # de bibliotecas HTTP. Usamos UA de browser real + Accept de RSS.
    HEADERS = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
        ),
        "Accept": "application/rss+xml, application/xml, text/xml, */*",
    }

    def __init__(self):
        self.timeout = 10  # Reduzido para 10 segundos
    
    async def collect_all(self, hours_back: int = 24) -> List[Dict]:
        """
        Coleta notícias de todos os feeds RSS em paralelo
        
        Args:
            hours_back: Quantas horas para trás buscar notícias
            
        Returns:
            Lista de notícias coletadas
        """
        all_news = []
        # UTC-aware para alinhar com as datas de published_parsed (que são GMT).
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours_back)
        
        # Coletar de todos os feeds em paralelo
        tasks = [
            self._collect_from_feed(feed_config, cutoff_time)
            for feed_config in self.RSS_FEEDS
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for i, result in enumerate(results):
            feed_name = self.RSS_FEEDS[i]['name']
            if isinstance(result, Exception):
                logger.error(f"Erro ao coletar de {feed_name}: {result}")
            elif isinstance(result, list):
                all_news.extend(result)
                logger.info(f"Coletadas {len(result)} notícias de {feed_name}")
        
        logger.info(f"Total de {len(all_news)} notícias coletadas de RSS feeds")
        return all_news
    
    async def _collect_from_feed(
        self, 
        feed_config: Dict, 
        cutoff_time: datetime
    ) -> List[Dict]:
        """Coleta notícias de um feed RSS específico"""
        news_items = []
        
        try:
            # Parse RSS feed
            feed = await self._fetch_feed(feed_config["url"])
            
            if not feed or not feed.entries:
                logger.warning(f"Nenhuma entrada encontrada em {feed_config['name']}")
                return news_items
            
            for entry in feed.entries:
                try:
                    # Parse publication date
                    pub_date = self._parse_date(entry)

                    # Filtrar por data. Entradas SEM data parseável são descartadas
                    # (não publicamos notícia de idade desconhecida — era assim que
                    # notícias antigas vazavam pelo filtro de recência).
                    if pub_date is None or pub_date < cutoff_time:
                        logger.debug(
                            f"Entrada descartada por data ({pub_date}): "
                            f"{entry.get('title', '')[:60]}"
                        )
                        continue
                    
                    # Extrair informações
                    news_item = {
                        "source": feed_config["name"],
                        "source_language": feed_config["language"],
                        "title": _strip_html(entry.get("title", "")),
                        "url": entry.get("link", "").strip(),
                        "description": _strip_html(entry.get("summary", "")),
                        "published_at": pub_date,
                        "collected_at": datetime.now(timezone.utc),
                    }
                    
                    # Validar dados mínimos
                    if news_item["title"] and news_item["url"]:
                        news_items.append(news_item)
                
                except Exception as e:
                    logger.warning(f"Erro ao processar entrada: {e}")
                    continue
        
        except Exception as e:
            logger.error(f"Erro ao coletar feed {feed_config['name']}: {e}")
        
        return news_items
    
    async def _fetch_feed(self, url: str) -> Optional[feedparser.FeedParserDict]:
        """Busca e parseia um feed RSS"""
        max_retries = 2
        
        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient(
                    timeout=self.timeout,
                    follow_redirects=True,
                    limits=httpx.Limits(max_connections=5),
                    headers=self.HEADERS,
                ) as client:
                    logger.debug(f"Tentativa {attempt + 1}/{max_retries} para {url}")
                    response = await client.get(url)
                    response.raise_for_status()
                    
                    # Parse feed
                    feed = feedparser.parse(response.text)
                    logger.debug(f"Feed {url} parseado com sucesso: {len(feed.entries)} entradas")
                    return feed
            
            except httpx.ConnectError as e:
                logger.warning(f"Erro de conexão ao buscar {url} (tentativa {attempt + 1}/{max_retries}): {e}")
                if attempt == max_retries - 1:
                    logger.error(f"Falha definitiva ao conectar em {url} após {max_retries} tentativas")
                    return None
            
            except httpx.TimeoutException as e:
                logger.warning(f"Timeout ao buscar {url} (tentativa {attempt + 1}/{max_retries}): {e}")
                if attempt == max_retries - 1:
                    logger.error(f"Timeout definitivo em {url} após {max_retries} tentativas")
                    return None

            except httpx.HTTPStatusError as e:
                status = e.response.status_code
                if status >= 500 and attempt < max_retries - 1:
                    logger.warning(
                        f"HTTP {status} ao buscar {url} "
                        f"(tentativa {attempt + 1}/{max_retries})"
                    )
                    continue
                # 4xx não adianta repetir: feed removido ou bloqueio anti-bot.
                logger.error(
                    f"Feed {url} respondeu HTTP {status} — "
                    f"verificar se o feed mudou de URL ou bloqueia bots"
                )
                return None

            except Exception as e:
                logger.error(f"Erro inesperado ao buscar feed {url}: {type(e).__name__}: {e}")
                return None
        
        return None
    
    def _parse_date(self, entry: feedparser.FeedParserDict) -> Optional[datetime]:
        """Parseia a data de publicação de uma entrada"""
        try:
            # Tentar diferentes campos de data
            # published_parsed/updated_parsed do feedparser são GMT; marcamos
            # como UTC-aware para comparar com o cutoff (também UTC-aware).
            if hasattr(entry, "published_parsed") and entry.published_parsed:
                return datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
            elif hasattr(entry, "updated_parsed") and entry.updated_parsed:
                return datetime(*entry.updated_parsed[:6], tzinfo=timezone.utc)
            else:
                return None
        except Exception:
            return None

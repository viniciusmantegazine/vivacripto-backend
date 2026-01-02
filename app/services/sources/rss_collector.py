"""
RSS Feed Collector Service
Coleta notícias de feeds RSS de fontes confiáveis
"""
import feedparser
import httpx
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from loguru import logger


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
            "name": "Bitcoin Magazine",
            "url": "https://bitcoinmagazine.com/.rss/full/",
            "language": "en"
        },
        {
            "name": "CryptoSlate",
            "url": "https://cryptoslate.com/feed/",
            "language": "en"
        },
    ]
    
    def __init__(self):
        self.timeout = 30
    
    async def collect_all(self, hours_back: int = 24) -> List[Dict]:
        """
        Coleta notícias de todos os feeds RSS
        
        Args:
            hours_back: Quantas horas para trás buscar notícias
            
        Returns:
            Lista de notícias coletadas
        """
        all_news = []
        cutoff_time = datetime.now() - timedelta(hours=hours_back)
        
        for feed_config in self.RSS_FEEDS:
            try:
                news = await self._collect_from_feed(feed_config, cutoff_time)
                all_news.extend(news)
                logger.info(f"Coletadas {len(news)} notícias de {feed_config['name']}")
            except Exception as e:
                logger.error(f"Erro ao coletar de {feed_config['name']}: {e}")
        
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
                    
                    # Filtrar por data
                    if pub_date and pub_date < cutoff_time:
                        continue
                    
                    # Extrair informações
                    news_item = {
                        "source": feed_config["name"],
                        "source_language": feed_config["language"],
                        "title": entry.get("title", "").strip(),
                        "url": entry.get("link", "").strip(),
                        "description": entry.get("summary", "").strip(),
                        "published_at": pub_date,
                        "collected_at": datetime.now(),
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
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url)
                response.raise_for_status()
                
                # Parse feed
                feed = feedparser.parse(response.text)
                return feed
        
        except Exception as e:
            logger.error(f"Erro ao buscar feed {url}: {e}")
            return None
    
    def _parse_date(self, entry: feedparser.FeedParserDict) -> Optional[datetime]:
        """Parseia a data de publicação de uma entrada"""
        try:
            # Tentar diferentes campos de data
            if hasattr(entry, "published_parsed") and entry.published_parsed:
                return datetime(*entry.published_parsed[:6])
            elif hasattr(entry, "updated_parsed") and entry.updated_parsed:
                return datetime(*entry.updated_parsed[:6])
            else:
                return None
        except Exception:
            return None

"""
News Aggregator Service
Agrega notícias de múltiplas fontes (RSS + APIs)
"""
from typing import List, Dict
from loguru import logger

from .rss_collector import RSSCollector
from .api_collector import APICollector


class NewsAggregator:
    """Agregador de notícias de múltiplas fontes"""
    
    def __init__(self):
        self.rss_collector = RSSCollector()
        self.api_collector = APICollector()
    
    async def collect_news(self, hours_back: int = 24) -> List[Dict]:
        """
        Coleta notícias de todas as fontes disponíveis
        
        Args:
            hours_back: Quantas horas para trás buscar notícias
            
        Returns:
            Lista agregada de notícias de todas as fontes
        """
        logger.info(f"Iniciando coleta de notícias (últimas {hours_back}h)")
        
        all_news = []
        
        # Coletar de RSS feeds
        try:
            logger.info("Coletando de RSS feeds...")
            rss_news = await self.rss_collector.collect_all(hours_back)
            all_news.extend(rss_news)
            logger.info(f"RSS feeds: {len(rss_news)} notícias coletadas")
        except Exception as e:
            logger.error(f"Erro ao coletar RSS feeds: {type(e).__name__}: {e}")
        
        # Coletar de APIs
        try:
            logger.info("Coletando de APIs externas...")
            api_news = await self.api_collector.collect_all(hours_back)
            all_news.extend(api_news)
            logger.info(f"APIs: {len(api_news)} notícias coletadas")
        except Exception as e:
            logger.error(f"Erro ao coletar de APIs: {type(e).__name__}: {e}")
        
        logger.info(f"Coleta finalizada: {len(all_news)} notícias no total")
        
        return all_news

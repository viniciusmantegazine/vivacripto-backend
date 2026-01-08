"""
API News Collector Service
Coleta notícias de APIs externas (CryptoPanic, CoinGecko)
"""
import httpx
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from loguru import logger

from app.core.config import settings


class APICollector:
    """Coletor de notícias via APIs externas"""
    
    def __init__(self):
        self.timeout = 10  # Reduzido para 10 segundos
        self.cryptopanic_api_key = settings.CRYPTOPANIC_API_KEY
    
    async def collect_all(self, hours_back: int = 24) -> List[Dict]:
        """
        Coleta notícias de todas as APIs
        
        Args:
            hours_back: Quantas horas para trás buscar notícias
            
        Returns:
            Lista de notícias coletadas
        """
        all_news = []
        
        # CryptoPanic
        if self.cryptopanic_api_key:
            try:
                news = await self._collect_from_cryptopanic(hours_back)
                all_news.extend(news)
                logger.info(f"Coletadas {len(news)} notícias do CryptoPanic")
            except Exception as e:
                logger.error(f"Erro ao coletar do CryptoPanic: {e}")
        
        logger.info(f"Total de {len(all_news)} notícias coletadas de APIs")
        return all_news
    
    async def _collect_from_cryptopanic(self, hours_back: int) -> List[Dict]:
        """Coleta notícias do CryptoPanic API"""
        news_items = []
        
        if not self.cryptopanic_api_key:
            logger.warning("CryptoPanic API key não configurada")
            return news_items
        
        try:
            url = "https://cryptopanic.com/api/v1/posts/"
            params = {
                "auth_token": self.cryptopanic_api_key,
                "kind": "news",  # Apenas notícias
                "filter": "rising",  # Notícias em alta
                "currencies": "BTC,ETH",  # Principais moedas
                "public": "true",
            }
            
            async with httpx.AsyncClient(
                timeout=self.timeout,
                follow_redirects=True
            ) as client:
                logger.debug(f"Buscando notícias do CryptoPanic...")
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
                logger.debug(f"CryptoPanic retornou {len(data.get('results', []))} notícias")
            
            cutoff_time = datetime.now() - timedelta(hours=hours_back)
            
            for item in data.get("results", []):
                try:
                    # Parse publication date
                    pub_date_str = item.get("published_at")
                    pub_date = datetime.fromisoformat(pub_date_str.replace("Z", "+00:00")) if pub_date_str else None
                    
                    # Filtrar por data
                    if pub_date and pub_date < cutoff_time:
                        continue
                    
                    news_item = {
                        "source": item.get("source", {}).get("title", "CryptoPanic"),
                        "source_language": "en",
                        "title": item.get("title", "").strip(),
                        "url": item.get("url", "").strip(),
                        "description": "",  # CryptoPanic não fornece descrição
                        "published_at": pub_date,
                        "collected_at": datetime.now(),
                        "metadata": {
                            "votes": item.get("votes", {}).get("positive", 0),
                            "currencies": [c.get("code") for c in item.get("currencies", [])],
                        }
                    }
                    
                    if news_item["title"] and news_item["url"]:
                        news_items.append(news_item)
                
                except Exception as e:
                    logger.warning(f"Erro ao processar item do CryptoPanic: {e}")
                    continue
        
        except httpx.ConnectError as e:
            logger.error(f"Erro de conexão ao buscar CryptoPanic API: {e}")
        except httpx.TimeoutException as e:
            logger.error(f"Timeout ao buscar CryptoPanic API: {e}")
        except Exception as e:
            logger.error(f"Erro inesperado ao buscar CryptoPanic API: {type(e).__name__}: {e}")
        
        return news_items

"""
News Aggregator Service
Agrega notícias de múltiplas fontes (RSS + APIs) com deduplicação inteligente
"""
from typing import List, Dict, Tuple
from loguru import logger

from .rss_collector import RSSCollector
from .api_collector import APICollector


class NewsAggregator:
    """Agregador de notícias de múltiplas fontes com deduplicação"""

    # Threshold de similaridade para considerar notícias como duplicatas
    # Mais baixo que o threshold de posts (0.80) para ser mais agressivo na filtragem
    SOURCE_DEDUP_THRESHOLD = 0.65

    def __init__(self):
        self.rss_collector = RSSCollector()
        self.api_collector = APICollector()
        self._similarity_engine = None

    def _get_similarity_engine(self):
        """Lazy loading do engine de similaridade"""
        if self._similarity_engine is None:
            try:
                from app.services.deduplication.similarity_engine import SimilarityFactory
                self._similarity_engine = SimilarityFactory.create("hybrid")
                logger.info("Engine de similaridade carregado para deduplicação de fontes")
            except Exception as e:
                logger.warning(f"Não foi possível carregar engine de similaridade: {e}")
        return self._similarity_engine

    async def collect_news(self, hours_back: int = 24) -> List[Dict]:
        """
        Coleta notícias de todas as fontes disponíveis

        Args:
            hours_back: Quantas horas para trás buscar notícias

        Returns:
            Lista agregada de notícias de todas as fontes (deduplicada)
        """
        logger.info(f"Iniciando coleta de notícias (últimas {hours_back}h)")
        logger.debug(f"RSS Collector: {self.rss_collector}")
        logger.debug(f"API Collector: {self.api_collector}")

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

        total_before = len(all_news)
        logger.info(f"Coleta finalizada: {total_before} notícias no total")

        # Deduplificar notícias de fontes diferentes sobre o mesmo tema
        deduplicated_news = self._deduplicate_source_news(all_news)

        removed = total_before - len(deduplicated_news)
        if removed > 0:
            logger.info(f"Deduplicação de fontes: {removed} notícias duplicadas removidas")

        logger.info(f"Notícias únicas para processamento: {len(deduplicated_news)}")

        return deduplicated_news

    def _deduplicate_source_news(self, news_list: List[Dict]) -> List[Dict]:
        """
        Remove notícias duplicadas de diferentes fontes sobre o mesmo tema.
        Mantém a notícia com descrição mais completa.

        Args:
            news_list: Lista de notícias coletadas

        Returns:
            Lista de notícias únicas
        """
        if len(news_list) <= 1:
            return news_list

        engine = self._get_similarity_engine()
        if engine is None:
            logger.warning("Engine de similaridade não disponível, retornando todas as notícias")
            return news_list

        # Marcar índices de notícias duplicadas
        duplicates = set()
        unique_news = []

        for i, news_i in enumerate(news_list):
            if i in duplicates:
                continue

            text_i = self._get_comparison_text(news_i)
            is_duplicate = False

            # Comparar com notícias já marcadas como únicas
            for j, news_j in enumerate(unique_news):
                text_j = self._get_comparison_text(news_j)

                try:
                    result = engine.calculate(text_i, text_j)
                    similarity = result.score

                    if similarity >= self.SOURCE_DEDUP_THRESHOLD:
                        # Notícias são similares - decidir qual manter
                        logger.debug(
                            f"Similaridade {similarity:.2%} detectada entre fontes:\n"
                            f"  1. [{news_i.get('source')}] {news_i.get('title', '')[:60]}...\n"
                            f"  2. [{news_j.get('source')}] {news_j.get('title', '')[:60]}..."
                        )

                        # Manter a notícia com descrição mais completa
                        desc_i = len(news_i.get('description', ''))
                        desc_j = len(news_j.get('description', ''))

                        if desc_i > desc_j:
                            # Substituir a existente pela nova (tem mais conteúdo)
                            idx = unique_news.index(news_j)
                            unique_news[idx] = news_i
                            logger.debug(f"  → Mantendo versão de [{news_i.get('source')}] (mais detalhada)")
                        else:
                            logger.debug(f"  → Mantendo versão de [{news_j.get('source')}] (mais detalhada)")

                        is_duplicate = True
                        break

                except Exception as e:
                    logger.warning(f"Erro ao calcular similaridade: {e}")
                    continue

            if not is_duplicate:
                unique_news.append(news_i)

        return unique_news

    def _get_comparison_text(self, news: Dict) -> str:
        """Extrai texto para comparação de similaridade"""
        title = news.get('title', '')
        description = news.get('description', '')
        return f"{title} {description}"

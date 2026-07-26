"""
News Aggregator Service
Agrega notícias de múltiplas fontes (RSS + APIs) com deduplicação inteligente
"""
import asyncio
from datetime import datetime, timezone
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
        """Lazy loading do engine de similaridade (TF-IDF para performance)"""
        if self._similarity_engine is None:
            try:
                from app.services.deduplication.similarity_engine import SimilarityFactory
                # Usar TF-IDF ao invés de hybrid para melhor performance
                # Embeddings são muito lentos para deduplicação de fontes em lote
                self._similarity_engine = SimilarityFactory.create("tfidf")
                logger.info("Engine TF-IDF carregado para deduplicação de fontes")
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

        # Deduplificar notícias de fontes diferentes sobre o mesmo tema.
        # O(n²) síncrono e CPU-bound (TF-IDF): roda fora do event loop.
        deduplicated_news = await asyncio.to_thread(self._deduplicate_source_news, all_news)

        removed = total_before - len(deduplicated_news)
        if removed > 0:
            logger.info(f"Deduplicação de fontes: {removed} notícias duplicadas removidas")

        logger.info(f"Notícias únicas para processamento: {len(deduplicated_news)}")

        return deduplicated_news

    def _deduplicate_source_news(self, news_list: List[Dict]) -> List[Dict]:
        """
        Remove notícias duplicadas de diferentes fontes sobre o mesmo tema.

        Mantém a notícia com descrição mais completa e CONTA quantas fontes
        cobriram cada tema (source_count) — esse é o sinal de relevância
        usado para ordenar o resultado: notícia coberta por mais fontes é
        mais importante e vai para o topo da fila de processamento.
        Empate é resolvido por recência (published_at).

        Args:
            news_list: Lista de notícias coletadas

        Returns:
            Lista de notícias únicas, ordenada por relevância
        """
        for news in news_list:
            news["source_count"] = 1
            news["covered_by"] = [news.get("source", "")]

        if len(news_list) <= 1:
            return news_list

        engine = self._get_similarity_engine()
        if engine is None:
            logger.warning("Engine de similaridade não disponível, retornando todas as notícias")
            return news_list

        logger.info(f"Iniciando deduplicação de {len(news_list)} notícias...")
        unique_news = []
        duplicates_found = 0

        for i, news_i in enumerate(news_list):
            text_i = self._get_comparison_text(news_i)
            is_duplicate = False

            # Comparar com notícias já marcadas como únicas
            for j, news_j in enumerate(unique_news):
                text_j = self._get_comparison_text(news_j)

                try:
                    similarity = engine.calculate(text_i, text_j).score
                except Exception as e:
                    logger.warning(f"Erro ao calcular similaridade: {e}")
                    continue

                if similarity >= self.SOURCE_DEDUP_THRESHOLD:
                    duplicates_found += 1
                    logger.debug(
                        f"Duplicata #{duplicates_found}: {similarity:.0%} - "
                        f"[{news_i.get('source')}] vs [{news_j.get('source')}]"
                    )

                    # Mantém a descrição mais completa, acumulando contagem
                    # de fontes e lista de cobertura de ambas as versões.
                    desc_i = len(news_i.get('description', ''))
                    desc_j = len(news_j.get('description', ''))
                    keeper = news_i if desc_i > desc_j else news_j
                    keeper["source_count"] = news_j["source_count"] + 1
                    keeper["covered_by"] = news_j["covered_by"] + [news_i.get("source", "")]
                    unique_news[j] = keeper

                    is_duplicate = True
                    break

            if not is_duplicate:
                unique_news.append(news_i)

            # Log de progresso a cada 10 notícias
            if (i + 1) % 10 == 0:
                logger.debug(f"Deduplicação: {i + 1}/{len(news_list)} processadas")

        # Ordena por relevância: mais fontes primeiro; empate -> mais recente.
        # published_at das fontes RSS é sempre UTC-aware; fallback aware para
        # itens sem data não quebrar a comparação.
        fallback_date = datetime.min.replace(tzinfo=timezone.utc)
        unique_news.sort(
            key=lambda n: (n["source_count"], n.get("published_at") or fallback_date),
            reverse=True,
        )

        logger.info(f"Deduplicação concluída: {duplicates_found} duplicatas encontradas")
        if unique_news:
            top = unique_news[0]
            logger.info(
                f"Top da fila: [{top['source_count']} fonte(s)] {top.get('title', '')[:60]}"
            )
        return unique_news

    def _get_comparison_text(self, news: Dict) -> str:
        """Extrai texto para comparação de similaridade"""
        title = news.get('title', '')
        description = news.get('description', '')
        return f"{title} {description}"

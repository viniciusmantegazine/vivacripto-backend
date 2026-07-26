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
from .relevance_filter import RelevanceFilter


class NewsAggregator:
    """Agregador de notícias de múltiplas fontes com deduplicação"""

    # Threshold de similaridade para considerar notícias como duplicatas.
    #
    # NÃO subir para 0.65 (valor anterior): com ele o threshold nunca
    # disparava. Medição sobre 3525 pares cross-fonte reais (96 notícias,
    # janela de 72h) com o engine TF-IDF:
    #
    #   - maior similaridade entre par de MESMA notícia: 0.525
    #   - primeiro falso positivo (notícias distintas):  0.403
    #   - duplicatas verdadeiras descem até:             0.384
    #
    # As faixas se sobrepõem, então não existe corte limpo. 0.45 casa 8 pares
    # verdadeiros com zero falsos e deixa 0.047 de folga até o primeiro falso
    # positivo. 0.42 casaria 11, mas com só 0.017 de margem numa amostra só.
    #
    # A escolha é conservadora de propósito, por assimetria de custo: falso
    # positivo DESCARTA uma notícia distinta e o leitor nunca a vê.
    #
    # ATENÇÃO — correção de uma afirmação anterior: este comentário dizia que
    # falso negativo era "absorvido pelo DuplicateDetector (threshold 0.80) na
    # hora de publicar". Isso é FALSO. Medido: duplicatas reais pontuam
    # 0.53-0.62 no engine TF-IDF que o detector usa (settings
    # DEDUPLICATION_ENGINE = "tfidf"), então o threshold de 0.80 nunca dispara
    # e aquela camada não pega nada hoje. Falso negativo aqui resulta em
    # conteúdo duplicado PUBLICADO, não em perda apenas do boost de
    # source_count.
    #
    # Enquanto o threshold do DuplicateDetector não for corrigido, os dois
    # tipos de erro custam. Ao revisitar este valor, verifique primeiro se
    # aquela camada voltou a funcionar.
    SOURCE_DEDUP_THRESHOLD = 0.45

    def __init__(self):
        self.rss_collector = RSSCollector()
        self.api_collector = APICollector()
        self.relevance_filter = RelevanceFilter()
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

        # Filtro de relevância ANTES da deduplicação: o dedup é O(n²), e este é
        # o funil único por onde passam RSS e API.
        coletadas = len(all_news)
        all_news = self._filter_off_topic(all_news)

        total_before = len(all_news)
        logger.info(
            f"Coleta finalizada: {coletadas} notícia(s) coletada(s), "
            f"{total_before} no tema"
        )

        # Deduplificar notícias de fontes diferentes sobre o mesmo tema.
        # O(n²) síncrono e CPU-bound (TF-IDF): roda fora do event loop.
        deduplicated_news = await asyncio.to_thread(self._deduplicate_source_news, all_news)

        removed = total_before - len(deduplicated_news)
        if removed > 0:
            logger.info(f"Deduplicação de fontes: {removed} notícias duplicadas removidas")

        logger.info(f"Notícias únicas para processamento: {len(deduplicated_news)}")

        return deduplicated_news

    def _filter_off_topic(self, news_list: List[Dict]) -> List[Dict]:
        """
        Remove notícias de outra editoria antes da deduplicação.

        Loga CADA descarte em WARNING, com o termo que o causou. Não é excesso:
        este projeto já calibrou dois thresholds fora da faixa onde o dado real
        cai — SOURCE_DEDUP_THRESHOLD a 0,65 e DEDUPLICATION_THRESHOLD a 0,80 —
        e nos dois casos o sintoma foi silêncio. Gate mal calibrado comendo
        notícia legítima é o mesmo modo de falha, com consequência pior. A ~6%
        de descarte são cerca de 7 linhas por run.
        """
        mantidas = []
        for news in news_list:
            termo = self.relevance_filter.rejection_reason(news)
            if termo is None:
                mantidas.append(news)
                continue
            logger.warning(
                f"Fora de tema (casou '{termo}', sem sinal de cripto): "
                f"[{str(news.get('source') or '')}] {str(news.get('title') or '')[:80]}"
            )

        descartadas = len(news_list) - len(mantidas)
        if descartadas:
            logger.warning(
                f"Filtro de relevância: {descartadas}/{len(news_list)} "
                f"notícia(s) descartada(s) por serem de outra editoria"
            )
        return mantidas

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

                    # Mantém a descrição mais completa, acumulando a cobertura
                    # de ambas as versões.
                    #
                    # source_count é derivado de covered_by DEDUPLICADO, não
                    # incrementado: este loop não pula pares da mesma fonte,
                    # então três artigos parecidos do mesmo veículo mergeavam
                    # e produziam source_count=3 com covered_by repetido —
                    # invertendo a premissa do ranking, porque veículo se
                    # repetindo (digest, matérias relacionadas) passava à
                    # frente de notícia realmente coberta por várias fontes.
                    desc_i = len(news_i.get('description', ''))
                    desc_j = len(news_j.get('description', ''))
                    keeper = news_i if desc_i > desc_j else news_j
                    keeper["covered_by"] = sorted(
                        set(news_j["covered_by"]) | {news_i.get("source", "")}
                    )
                    keeper["source_count"] = len(keeper["covered_by"])
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

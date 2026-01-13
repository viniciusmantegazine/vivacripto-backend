"""
News Automation Pipeline
Orquestra todo o fluxo de automação de notícias.
Utiliza serviços especializados para cada etapa do processo.
"""
import traceback
from datetime import datetime, timezone
from typing import Dict
from uuid import uuid4

import httpx
import sentry_sdk
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.metrics import MetricsCollector
from app.crud.crud_post import crud_post
from app.services.ai.content_generator import ContentGenerator
from app.services.ai.image_generator import ImageGenerator
from app.services.automation.article_publisher import ArticlePublisher
from app.services.automation.quality_validator import QualityValidator
from app.services.deduplication import (
    ActionType,
    DuplicateDetector,
    NewsAssignment,
    PostRepositoryImpl,
)
from app.services.sources.news_aggregator import NewsAggregator
from app.services.ai.category_classifier import CategoryClassifier


class NewsPipeline:
    """
    Pipeline de automação de notícias.

    Orquestra o fluxo completo:
    1. Coleta de notícias (NewsAggregator)
    2. Geração de conteúdo (ContentGenerator)
    3. Validação de qualidade (QualityValidator)
    4. Detecção de duplicatas (DuplicateDetector)
    5. Publicação/Atualização (ArticlePublisher)
    """

    # Usar configurações de settings (com fallback para valores padrão)
    MAX_POSTS_PER_DAY = settings.DAILY_POST_LIMIT
    POSTS_PER_EXECUTION = settings.POSTS_PER_EXECUTION

    def __init__(self):
        self.aggregator = NewsAggregator()
        self.content_generator = ContentGenerator()
        self.image_generator = ImageGenerator()
        self.validator = QualityValidator()
        self.publisher = ArticlePublisher(self.image_generator)
        self.category_classifier = CategoryClassifier()
    
    async def run(self, db: AsyncSession) -> Dict:
        """
        Executa o pipeline completo de automação

        Returns:
            Relatório da execução com estatísticas e métricas de performance
        """
        run_id = str(uuid4())[:8]
        metrics = MetricsCollector(run_id)

        logger.info("=" * 60)
        logger.info(f"INICIANDO PIPELINE DE AUTOMAÇÃO DE NOTÍCIAS [run_id={run_id}]")
        logger.info("=" * 60)

        start_time = datetime.now(timezone.utc)
        report = {
            "run_id": run_id,
            "started_at": start_time,
            "status": "running",
            "collected": 0,
            "processed": 0,
            "published": 0,
            "updated": 0,
            "failed": 0,
            "errors": [],
        }

        try:
            # 1. Verificar limite diário
            logger.info("Verificando limite diário de posts...")
            if not await self._check_daily_limit(db):
                report["status"] = "skipped"
                report["message"] = f"Limite diário de {self.MAX_POSTS_PER_DAY} posts atingido"
                logger.warning(report["message"])
                return report

            # 2. Coletar notícias (com métricas)
            logger.info("\n[FASE 1] Coletando notícias das fontes...")
            try:
                with metrics.measure("collection"):
                    news_items = await self.aggregator.collect_news(hours_back=24)
                metrics.metrics.news_collected = len(news_items)
                report["collected"] = len(news_items)
            except Exception as e:
                logger.error(f"Erro ao coletar notícias: {type(e).__name__}: {e}")
                metrics.record_error(f"Collection failed: {e}")
                raise

            if not news_items:
                report["status"] = "completed"
                report["message"] = "Nenhuma notícia nova encontrada"
                logger.info(report["message"])
                metrics.finalize()
                metrics.log_summary()
                report["metrics"] = metrics.get_metrics_dict()
                return report

            # 3. Processar com detector de duplicatas
            logger.info("\n[FASE 2] Verificando duplicatas e processando notícias...")

            repo = PostRepositoryImpl(db)
            detector = DuplicateDetector(
                repository=repo,
                similarity_threshold=getattr(settings, 'DEDUPLICATION_THRESHOLD', 0.80),
                engine_type=getattr(settings, 'DEDUPLICATION_ENGINE', 'embedding')
            )

            remaining_slots = await self._get_remaining_daily_slots(db)
            posts_to_process = min(self.POSTS_PER_EXECUTION, remaining_slots, len(news_items))
            logger.info(f"Processando até {posts_to_process} notícia(s) (slots disponíveis: {remaining_slots})")

            processed_count = 0

            for i, source_news in enumerate(news_items[:posts_to_process], 1):
                try:
                    logger.info(f"\n--- Notícia {i}/{posts_to_process} ---")
                    logger.info(f"Título: {source_news.get('title', '')[:80]}...")

                    # Pré-classificar categoria para ajuste de tom na geração
                    title = source_news.get('title', '')
                    description = source_news.get('description', '')
                    category = self.category_classifier.classify(title, description, "")
                    logger.info(f"Categoria detectada: {category}")

                    # Gerar artigo com categoria para ajuste de tom (com métricas)
                    with metrics.measure("content_generation", title=title[:50]):
                        article = await self.content_generator.generate_article(source_news, category=category)

                    if not article:
                        logger.warning("Falha ao gerar artigo")
                        metrics.record_failure()
                        report["failed"] += 1
                        continue

                    # Validar qualidade (com métricas)
                    is_valid, errors = self.validator.validate_article(article)
                    metrics.record_validation(is_valid)

                    if not is_valid:
                        logger.warning(f"Artigo reprovado: {', '.join(errors)}")
                        metrics.record_failure()
                        report["failed"] += 1
                        report["errors"].extend(errors)
                        continue

                    # Criar NewsAssignment para o detector
                    assignment = NewsAssignment(
                        titulo=article["title"],
                        resumo=article.get("excerpt", ""),
                        conteudo=article["content_markdown"],
                        fonte=source_news.get("source_name", ""),
                        timestamp=datetime.now(timezone.utc).isoformat()
                    )

                    # Verificar duplicatas (com métricas)
                    with metrics.measure("deduplication"):
                        check_result = await detector.check_duplicate(assignment)

                    if check_result.acao == ActionType.CREATE_NEW:
                        logger.info("✨ Ação: CRIAR NOVO POST")

                        published = await self.publisher.publish_article(article, db)
                        if published:
                            metrics.record_publish()
                            report["published"] += 1
                            processed_count += 1
                            logger.info("✓ Artigo publicado com sucesso")
                        else:
                            metrics.record_failure()
                            report["failed"] += 1

                    elif check_result.acao == ActionType.UPDATE_EXISTING:
                        logger.info(
                            f"➕ Ação: ATUALIZAR POST EXISTENTE (ID: {check_result.post_existente_id})"
                        )
                        metrics.metrics.duplicates_found += 1

                        updated = await self.publisher.update_article(
                            check_result.post_existente_id, article, db
                        )
                        if updated:
                            metrics.record_update()
                            report["updated"] += 1
                            processed_count += 1
                            logger.info(f"✓ Post atualizado com sucesso")
                        else:
                            metrics.record_failure()
                            report["failed"] += 1

                except Exception as e:
                    logger.error(f"Erro ao processar notícia: {e}")
                    logger.error(f"Traceback: {traceback.format_exc()}")
                    metrics.record_error(str(e))
                    metrics.record_failure()
                    report["failed"] += 1
                    report["errors"].append(str(e))

            # 4. Revalidar frontend se houver mudanças
            if (report["published"] + report["updated"]) > 0:
                await self._revalidate_frontend()

            # Finalizar métricas
            metrics.finalize()
            metrics.log_summary()

            report["status"] = "completed"
            report["processed"] = processed_count
            report["completed_at"] = datetime.now(timezone.utc)
            report["duration_seconds"] = (report["completed_at"] - start_time).total_seconds()
            report["metrics"] = metrics.get_metrics_dict()

            logger.info("\n" + "=" * 60)
            logger.info("PIPELINE CONCLUÍDO")
            logger.info(f"Run ID: {run_id}")
            logger.info(f"Coletadas: {report['collected']}")
            logger.info(f"Processadas: {report['processed']}")
            logger.info(f"Publicadas: {report['published']}")
            logger.info(f"Atualizadas: {report['updated']}")
            logger.info(f"Falhas: {report['failed']}")
            logger.info(f"Duração: {report['duration_seconds']:.1f}s")
            logger.info("=" * 60)

            return report

        except Exception as e:
            logger.error(f"Erro fatal no pipeline: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            metrics.record_error(f"Fatal error: {e}")
            metrics.finalize()
            report["status"] = "error"
            report["error"] = str(e)
            report["metrics"] = metrics.get_metrics_dict()
            return report
    
    async def _check_daily_limit(self, db: AsyncSession) -> bool:
        """Verifica se o limite diário de posts foi atingido"""
        try:
            logger.debug("Consultando posts de hoje no banco de dados...")
            # Usar datetime naive (sem timezone) para compatibilidade com TIMESTAMP WITHOUT TIME ZONE
            today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            today_posts = await crud_post.get_recent_posts(db, since=today_start)
            logger.debug(f"Posts hoje: {len(today_posts)}/{self.MAX_POSTS_PER_DAY}")
            return len(today_posts) < self.MAX_POSTS_PER_DAY
        except Exception as e:
            logger.error(f"Erro ao verificar limite diário: {type(e).__name__}: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise

    async def _get_remaining_daily_slots(self, db: AsyncSession) -> int:
        """Retorna quantos posts ainda podem ser publicados hoje"""
        # Usar datetime naive (sem timezone) para compatibilidade com TIMESTAMP WITHOUT TIME ZONE
        today_start = datetime.utcnow().replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        today_posts = await crud_post.get_recent_posts(db, since=today_start)
        return max(0, self.MAX_POSTS_PER_DAY - len(today_posts))

    async def _revalidate_frontend(self):
        """Revalida o frontend Next.js (ISR)"""
        try:
            if not settings.FRONTEND_URL:
                logger.warning("FRONTEND_URL não configurada, pulando revalidação")
                return
            
            revalidate_url = f"{settings.FRONTEND_URL}/api/revalidate"
            
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(
                    revalidate_url,
                    json={"secret": settings.REVALIDATE_SECRET}
                )
                
                if response.status_code == 200:
                    logger.info("✓ Frontend revalidado com sucesso")
                else:
                    logger.warning(f"Falha ao revalidar frontend: {response.status_code}")
        
        except Exception as e:
            logger.warning(f"Erro ao revalidar frontend: {e}")

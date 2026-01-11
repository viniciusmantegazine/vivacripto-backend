"""
News Automation Pipeline
Orquestra todo o fluxo de automação de notícias
"""
from typing import List, Dict
from datetime import datetime, timedelta
from uuid import UUID
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
import markdown
import httpx
import sentry_sdk

from app.services.sources.news_aggregator import NewsAggregator
from app.services.deduplication import DuplicateDetector, NewsAssignment, ActionType, PostRepositoryImpl
from app.services.ai.content_generator import ContentGenerator
from app.services.ai.image_generator import ImageGenerator
from app.services.automation.quality_validator import QualityValidator
from app.services.ai.category_classifier import category_classifier
from app.crud.crud_post import crud_post
from app.db.models import Category
from app.schemas.post import PostCreate, PostUpdate
from app.core.config import settings


class NewsPipeline:
    """Pipeline de automação de notícias"""
    
    MAX_POSTS_PER_DAY = 10  # Limite diário de publicações
    POSTS_PER_EXECUTION = 1  # Publicar apenas 1 notícia por chamada do endpoint
    
    def __init__(self):
        self.aggregator = NewsAggregator()
        self.content_generator = ContentGenerator()
        self.image_generator = ImageGenerator()
        self.validator = QualityValidator()
    
    async def run(self, db: AsyncSession) -> Dict:
        """
        Executa o pipeline completo de automação
        
        Returns:
            Relatório da execução com estatísticas
        """
        logger.info("=" * 60)
        logger.info("INICIANDO PIPELINE DE AUTOMAÇÃO DE NOTÍCIAS")
        logger.info("=" * 60)
        
        start_time = datetime.now()
        report = {
            "started_at": start_time,
            "status": "running",
            "collected": 0,
            "processed": 0,
            "published": 0,
            "updated": 0,
            "review_manual": 0,
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
            
            # 2. Coletar notícias
            logger.info("\n[FASE 1] Coletando notícias das fontes...")
            try:
                news_items = await self.aggregator.collect_news(hours_back=24)
                report["collected"] = len(news_items)
            except Exception as e:
                logger.error(f"Erro ao coletar notícias: {type(e).__name__}: {e}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
                raise
            
            if not news_items:
                report["status"] = "completed"
                report["message"] = "Nenhuma notícia nova encontrada"
                logger.info(report["message"])
                return report
            
            # 3. Processar com detector de duplicatas
            logger.info("\n[FASE 2] Verificando duplicatas e processando notícias...")
            
            # Inicializar detector com repositório
            repo = PostRepositoryImpl(db)
            detector = DuplicateDetector(
                repository=repo,
                similarity_threshold=getattr(settings, 'DEDUPLICATION_THRESHOLD', 0.80),
                engine_type=getattr(settings, 'DEDUPLICATION_ENGINE', 'embedding')
            )
            
            # Limitar processamento
            remaining_slots = await self._get_remaining_daily_slots(db)
            posts_to_process = min(self.POSTS_PER_EXECUTION, remaining_slots, len(news_items))
            logger.info(f"Processando até {posts_to_process} notícia(s) (slots disponíveis: {remaining_slots})")
            
            processed_count = 0
            
            for i, source_news in enumerate(news_items[:posts_to_process], 1):
                try:
                    logger.info(f"\n--- Notícia {i}/{posts_to_process} ---")
                    logger.info(f"Título: {source_news.get('title', '')[:80]}...")
                    
                    # Gerar artigo primeiro
                    article = await self.content_generator.generate_article(source_news)
                    if not article:
                        logger.warning("Falha ao gerar artigo")
                        report["failed"] += 1
                        continue
                    
                    # Validar qualidade
                    is_valid, errors = self.validator.validate_article(article)
                    if not is_valid:
                        logger.warning(f"Artigo reprovado: {', '.join(errors)}")
                        report["failed"] += 1
                        report["errors"].extend(errors)
                        continue
                    
                    # Criar NewsAssignment para o detector
                    assignment = NewsAssignment(
                        titulo=article["title"],
                        resumo=article.get("excerpt", ""),
                        conteudo=article["content_markdown"],
                        fonte=source_news.get("source_name", ""),
                        timestamp=datetime.utcnow().isoformat()
                    )
                    
                    # Verificar duplicatas
                    check_result = await detector.check_duplicate(assignment)
                    
                    if check_result.acao == ActionType.CREATE_NEW:
                        logger.info(f"✨ Ação: CRIAR NOVO POST")
                        
                        # Publicar artigo
                        published = await self._publish_article(article, db)
                        if published:
                            report["published"] += 1
                            processed_count += 1
                            logger.info(f"✓ Artigo publicado com sucesso")
                        else:
                            report["failed"] += 1
                    
                    elif check_result.acao == ActionType.UPDATE_EXISTING:
                        logger.info(f"➕ Ação: ATUALIZAR POST EXISTENTE (ID: {check_result.post_existente_id})")
                        
                        # Atualizar post existente com novo conteúdo
                        updated = await self._update_existing_post(
                            check_result.post_existente_id,
                            article,
                            db
                        )
                        if updated:
                            report["updated"] += 1
                            processed_count += 1
                            logger.info(f"✓ Post atualizado com sucesso")
                        else:
                            report["failed"] += 1
                    
                    elif check_result.acao == ActionType.REVIEW_MANUAL:
                        logger.warning(f"⚠️ Ação: REVISÃO MANUAL NECESSÁRIA")
                        logger.warning(f"Similaridade máxima: {check_result.similaridade_maxima:.2f}")
                        logger.warning(f"Candidatos similares: {len(check_result.candidatos_similares)}")
                        
                        report["review_manual"] += 1
                        
                        # Enviar para Sentry para análise
                        sentry_sdk.capture_message(
                            f"Pauta para revisão manual: {assignment.titulo}",
                            level="warning",
                            extras={
                                "similaridade": check_result.similaridade_maxima,
                                "candidatos": check_result.candidatos_similares,
                                "titulo": assignment.titulo
                            }
                        )
                
                except Exception as e:
                    logger.error(f"Erro ao processar notícia: {e}")
                    import traceback
                    logger.error(f"Traceback: {traceback.format_exc()}")
                    report["failed"] += 1
                    report["errors"].append(str(e))
            
            # 4. Revalidar frontend se houver mudanças
            if (report["published"] + report["updated"]) > 0:
                await self._revalidate_frontend()
            
            report["status"] = "completed"
            report["processed"] = processed_count
            report["completed_at"] = datetime.now()
            report["duration_seconds"] = (report["completed_at"] - start_time).total_seconds()
            
            logger.info("\n" + "=" * 60)
            logger.info("PIPELINE CONCLUÍDO")
            logger.info(f"Coletadas: {report['collected']}")
            logger.info(f"Processadas: {report['processed']}")
            logger.info(f"Publicadas: {report['published']}")
            logger.info(f"Atualizadas: {report['updated']}")
            logger.info(f"Revisão Manual: {report['review_manual']}")
            logger.info(f"Falhas: {report['failed']}")
            logger.info(f"Duração: {report['duration_seconds']:.1f}s")
            logger.info("=" * 60)
            
            return report
        
        except Exception as e:
            logger.error(f"Erro fatal no pipeline: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            report["status"] = "error"
            report["error"] = str(e)
            return report
    
    async def _check_daily_limit(self, db: AsyncSession) -> bool:
        """Verifica se o limite diário de posts foi atingido"""
        try:
            logger.debug("Consultando posts de hoje no banco de dados...")
            today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
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
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_posts = await crud_post.get_recent_posts(db, since=today_start)
        return max(0, self.MAX_POSTS_PER_DAY - len(today_posts))
    
    async def _publish_article(self, article: Dict, db: AsyncSession) -> bool:
        """Publica um artigo no banco de dados"""
        try:
            # Converter markdown para HTML
            content_html = markdown.markdown(
                article["content_markdown"],
                extensions=['extra', 'codehilite']
            )
            
            # Classificar categoria automaticamente
            category_slug = category_classifier.classify(
                title=article["title"],
                content=article["content_markdown"],
                excerpt=article.get("excerpt", "")
            )
            
            # Buscar categoria no banco
            from sqlalchemy import select
            result = await db.execute(
                select(Category).where(Category.slug == category_slug)
            )
            category = result.scalar_one_or_none()
            
            if not category:
                logger.warning(f"Category '{category_slug}' not found in database, creating...")
                category = Category(
                    name=category_classifier.get_category_name(category_slug),
                    slug=category_slug
                )
                db.add(category)
                await db.flush()
            
            # Gerar imagem
            image_url = await self.image_generator.generate_and_upload_image(
                article["title"],
                article["content_markdown"]
            )
            
            # Criar post com validação de tamanho dos campos meta
            meta_title = article.get("meta_title", "")
            meta_description = article.get("meta_description", "")
            
            # Truncar meta_title para 70 caracteres
            if meta_title and len(meta_title) > 70:
                meta_title = meta_title[:67] + "..."
            
            # Truncar meta_description para 160 caracteres
            if meta_description and len(meta_description) > 160:
                meta_description = meta_description[:157] + "..."
            
            post_data = PostCreate(
                title=article["title"],
                slug=article["slug"],
                content_markdown=article["content_markdown"],
                content_html=content_html,
                excerpt=article.get("excerpt"),
                featured_image_url=image_url or article.get("featured_image_url"),
                status="published",
                published_at=datetime.now(),
                meta_title=meta_title or None,
                meta_description=meta_description or None,
                canonical_url=None,
                category_id=category.id,
            )
            
            await crud_post.create_post(db, post_data)
            await db.commit()
            
            return True
        
        except Exception as e:
            logger.error(f"Erro ao publicar artigo: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            await db.rollback()
            return False
    
    async def _update_existing_post(self, post_id: str, article: Dict, db: AsyncSession) -> bool:
        """Atualiza um post existente com novo conteúdo"""
        try:
            # Converter markdown para HTML
            content_html = markdown.markdown(
                article["content_markdown"],
                extensions=['extra', 'codehilite']
            )
            
            # Atualizar post
            post_update = PostUpdate(
                content_markdown=article["content_markdown"],
                content_html=content_html,
                updated_at=datetime.now()
            )
            
            await crud_post.update_post(db, post_id=UUID(post_id), post_in=post_update)
            await db.commit()
            
            logger.info(f"Post {post_id} atualizado com novo conteúdo")
            return True
        
        except Exception as e:
            logger.error(f"Erro ao atualizar post: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            await db.rollback()
            return False
    
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

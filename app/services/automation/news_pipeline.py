"""
News Automation Pipeline
Orquestra todo o fluxo de automação de notícias
"""
from typing import List, Dict
from datetime import datetime, timedelta
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
import markdown
import httpx

from app.services.sources.news_aggregator import NewsAggregator
from app.services.automation.deduplication import DeduplicationService
from app.services.ai.content_generator import ContentGenerator
from app.services.ai.image_generator import ImageGenerator
from app.services.automation.quality_validator import QualityValidator
from app.services.ai.category_classifier import category_classifier
from app.crud.crud_post import crud_post
from app.db.models import Category
from app.schemas.post import PostCreate
from app.core.config import settings


class NewsPipeline:
    """Pipeline de automação de notícias"""
    
    MAX_POSTS_PER_DAY = 1  # Gerar apenas 1 notícia por execução
    
    def __init__(self):
        self.aggregator = NewsAggregator()
        self.deduplicator = DeduplicationService()
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
            "filtered": 0,
            "generated": 0,
            "published": 0,
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
            
            # 3. Filtrar e deduplic ar
            logger.info("\n[FASE 2] Filtrando e removendo duplicatas...")
            unique_news = await self.deduplicator.filter_and_deduplicate(news_items, db)
            report["filtered"] = len(unique_news)
            
            if not unique_news:
                report["status"] = "completed"
                report["message"] = "Todas as notícias eram duplicadas ou irrelevantes"
                logger.info(report["message"])
                return report
            
            # 4. Limitar ao número de posts restantes do dia
            remaining_slots = await self._get_remaining_daily_slots(db)
            unique_news = unique_news[:remaining_slots]
            logger.info(f"Processando {len(unique_news)} notícias (slots disponíveis: {remaining_slots})")
            
            # 5. Gerar e publicar artigos
            logger.info("\n[FASE 3] Gerando e publicando artigos...")
            for i, source_news in enumerate(unique_news, 1):
                try:
                    logger.info(f"\n--- Artigo {i}/{len(unique_news)} ---")
                    
                    # Gerar conteúdo
                    article = await self.content_generator.generate_article(source_news)
                    if not article:
                        report["failed"] += 1
                        continue
                    
                    report["generated"] += 1
                    
                    # Validar qualidade
                    is_valid, errors = self.validator.validate_article(article)
                    if not is_valid:
                        logger.warning(f"Artigo reprovado: {', '.join(errors)}")
                        report["failed"] += 1
                        report["errors"].extend(errors)
                        continue
                    
                    # Gerar imagem
                    image_url = await self.image_generator.generate_and_upload_image(
                        article["title"],
                        article["content_markdown"]
                    )
                    if image_url:
                        article["featured_image_url"] = image_url
                    
                    # Publicar
                    published = await self._publish_article(article, db)
                    if published:
                        report["published"] += 1
                        logger.info(f"✓ Artigo publicado: {article['title']}")
                    else:
                        report["failed"] += 1
                
                except Exception as e:
                    logger.error(f"Erro ao processar notícia: {e}")
                    report["failed"] += 1
                    report["errors"].append(str(e))
            
            # 6. Revalidar frontend (ISR)
            if report["published"] > 0:
                await self._revalidate_frontend()
            
            report["status"] = "completed"
            report["completed_at"] = datetime.now()
            report["duration_seconds"] = (report["completed_at"] - start_time).total_seconds()
            
            logger.info("\n" + "=" * 60)
            logger.info("PIPELINE CONCLUÍDO")
            logger.info(f"Coletadas: {report['collected']}")
            logger.info(f"Filtradas: {report['filtered']}")
            logger.info(f"Geradas: {report['generated']}")
            logger.info(f"Publicadas: {report['published']}")
            logger.info(f"Falhas: {report['failed']}")
            logger.info(f"Duração: {report['duration_seconds']:.1f}s")
            logger.info("=" * 60)
            
            return report
        
        except Exception as e:
            logger.error(f"Erro fatal no pipeline: {e}")
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
            
            # Criar post
            post_data = PostCreate(
                title=article["title"],
                slug=article["slug"],
                content_markdown=article["content_markdown"],
                content_html=content_html,
                excerpt=article.get("excerpt"),
                featured_image_url=article.get("featured_image_url"),
                status="published",
                published_at=datetime.now(),
                meta_title=article.get("meta_title"),
                meta_description=article.get("meta_description"),
                canonical_url=None,
                category_id=category.id,
            )
            
            await crud_post.create_post(db, post_data)
            await db.commit()
            
            return True
        
        except Exception as e:
            logger.error(f"Erro ao publicar artigo: {e}")
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

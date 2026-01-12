"""
Article Publisher Service
Responsável pela publicação e atualização de artigos no banco de dados.
Separa a lógica de persistência do pipeline principal.
"""
import traceback
from datetime import datetime, timezone
from typing import Dict, Optional
from uuid import UUID

import markdown
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.crud_post import crud_post
from app.db.models import Category
from app.schemas.post import PostCreate, PostUpdate
from app.services.ai.category_classifier import category_classifier
from app.services.ai.image_generator import ImageGenerator


class ArticlePublisher:
    """
    Serviço responsável por publicar e atualizar artigos.
    Encapsula a lógica de persistência e geração de assets.
    """

    def __init__(self, image_generator: Optional[ImageGenerator] = None):
        """
        Args:
            image_generator: Instância do gerador de imagens. Se None, cria uma nova.
        """
        self.image_generator = image_generator or ImageGenerator()

    async def publish_article(self, article: Dict, db: AsyncSession) -> bool:
        """
        Publica um novo artigo no banco de dados.

        Args:
            article: Dicionário com dados do artigo (title, slug, content_markdown, etc.)
            db: Sessão do banco de dados

        Returns:
            True se publicado com sucesso, False caso contrário
        """
        try:
            # Converter markdown para HTML
            content_html = self._convert_markdown_to_html(article["content_markdown"])

            # Classificar categoria automaticamente
            category = await self._get_or_create_category(article, db)

            # Gerar imagem
            image_url = await self._generate_image(article)

            # Preparar dados do post com validação de campos meta
            post_data = self._prepare_post_data(article, content_html, image_url, category.id)

            await crud_post.create_post(db, post_data, auto_commit=False)
            await db.commit()

            logger.info(f"Artigo '{article['title'][:50]}...' publicado com sucesso")
            return True

        except Exception as e:
            logger.error(f"Erro ao publicar artigo: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            await db.rollback()
            return False

    async def update_article(
        self, post_id: str, article: Dict, db: AsyncSession
    ) -> bool:
        """
        Atualiza um artigo existente com novo conteúdo.

        Args:
            post_id: ID do post a ser atualizado
            article: Dicionário com novos dados do artigo
            db: Sessão do banco de dados

        Returns:
            True se atualizado com sucesso, False caso contrário
        """
        try:
            # Converter markdown para HTML
            content_html = self._convert_markdown_to_html(article["content_markdown"])

            # Atualizar post
            post_update = PostUpdate(
                content_markdown=article["content_markdown"],
                content_html=content_html,
                updated_at=datetime.now(timezone.utc),
            )

            await crud_post.update_post(
                db, post_id=UUID(post_id), post_in=post_update, auto_commit=False
            )
            await db.commit()

            logger.info(f"Post {post_id} atualizado com novo conteúdo")
            return True

        except Exception as e:
            logger.error(f"Erro ao atualizar post: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            await db.rollback()
            return False

    def _convert_markdown_to_html(self, content_markdown: str) -> str:
        """Converte conteúdo markdown para HTML."""
        return markdown.markdown(
            content_markdown,
            extensions=["extra", "codehilite"],
        )

    async def _get_or_create_category(
        self, article: Dict, db: AsyncSession
    ) -> Category:
        """
        Busca ou cria a categoria para o artigo.

        Args:
            article: Dados do artigo para classificação
            db: Sessão do banco de dados

        Returns:
            Instância da categoria
        """
        category_slug = category_classifier.classify(
            title=article["title"],
            content=article["content_markdown"],
            excerpt=article.get("excerpt", ""),
        )

        result = await db.execute(
            select(Category).where(Category.slug == category_slug)
        )
        category = result.scalar_one_or_none()

        if not category:
            logger.warning(f"Category '{category_slug}' not found, creating...")
            category = Category(
                name=category_classifier.get_category_name(category_slug),
                slug=category_slug,
            )
            db.add(category)
            await db.flush()

        return category

    async def _generate_image(self, article: Dict) -> Optional[str]:
        """
        Gera e faz upload da imagem de destaque.

        Args:
            article: Dados do artigo

        Returns:
            URL da imagem ou None se falhar
        """
        try:
            return await self.image_generator.generate_and_upload_image(
                article["title"],
                article["content_markdown"],
            )
        except Exception as e:
            logger.warning(f"Erro ao gerar imagem: {e}")
            return None

    def _prepare_post_data(
        self,
        article: Dict,
        content_html: str,
        image_url: Optional[str],
        category_id: UUID,
    ) -> PostCreate:
        """
        Prepara os dados do post com validação de campos.

        Args:
            article: Dados do artigo
            content_html: Conteúdo HTML convertido
            image_url: URL da imagem de destaque
            category_id: ID da categoria

        Returns:
            Schema PostCreate pronto para persistência
        """
        meta_title = article.get("meta_title", "")
        meta_description = article.get("meta_description", "")

        # Truncar meta_title para 70 caracteres
        if meta_title and len(meta_title) > 70:
            meta_title = meta_title[:67] + "..."

        # Truncar meta_description para 160 caracteres
        if meta_description and len(meta_description) > 160:
            meta_description = meta_description[:157] + "..."

        return PostCreate(
            title=article["title"],
            slug=article["slug"],
            content_markdown=article["content_markdown"],
            content_html=content_html,
            excerpt=article.get("excerpt"),
            featured_image_url=image_url or article.get("featured_image_url"),
            status="published",
            published_at=datetime.now(timezone.utc),
            meta_title=meta_title or None,
            meta_description=meta_description or None,
            canonical_url=None,
            category_id=category_id,
        )

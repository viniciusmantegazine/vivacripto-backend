"""
Implementação concreta do PostRepository para o VivaCripto Backend
"""

from datetime import datetime, timedelta
from typing import List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

# Importações do projeto VivaCripto
from app.crud.crud_post import crud_post
from app.db.models import Post as PostModel
from app.schemas.post import PostCreate, PostUpdate

# Importações do módulo de deduplicação
from .duplicate_detector import PostRepository, PublishedPost


class PostRepositoryImpl(PostRepository):
    """
    Implementa a interface PostRepository usando o CRUD existente do projeto.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_posts_last_24h(self) -> List[PublishedPost]:
        """Busca posts publicados nas últimas 24 horas usando o crud_post."""
        since_time = datetime.utcnow() - timedelta(hours=24)
        
        # A função get_recent_posts já existe no crud_post.py
        recent_posts_models = await crud_post.get_recent_posts(self.db, since=since_time)
        
        # Converte o modelo SQLAlchemy (Post) para o dataclass (PublishedPost)
        return [self._convert_model_to_dataclass(p) for p in recent_posts_models]

    async def get_post_by_id(self, post_id: str) -> Optional[PublishedPost]:
        """Busca um post pelo ID."""
        post_model = await crud_post.get_post_by_id(self.db, post_id=UUID(post_id))
        if not post_model:
            return None
        return self._convert_model_to_dataclass(post_model)

    async def save_post(self, post_dataclass: PublishedPost) -> str:
        """Cria um novo post no banco de dados."""
        # Converte o dataclass para o schema Pydantic esperado pelo CRUD
        post_in = PostCreate(
            title=post_dataclass.titulo,
            content_markdown=post_dataclass.conteudo,
            excerpt=post_dataclass.resumo,
            author_id=None,  # Será definido pelo pipeline
            category_id=None,  # Será definido pelo pipeline
            status='draft'  # Será publicado pelo pipeline após validação
        )
        
        new_post_model = await crud_post.create_post(self.db, post_in=post_in)
        return str(new_post_model.id)

    async def update_post(self, post_dataclass: PublishedPost) -> None:
        """Atualiza um post existente."""
        # Atualizar o conteúdo e o histórico de deduplicação
        post_update_schema = PostUpdate(
            content_markdown=post_dataclass.conteudo,
            updated_at=datetime.fromisoformat(post_dataclass.data_atualizacao)
        )
        
        await crud_post.update_post(
            self.db,
            post_id=UUID(post_dataclass.id),
            post_in=post_update_schema
        )

    def _convert_model_to_dataclass(self, post_model: PostModel) -> PublishedPost:
        """Função utilitária para converter o modelo do DB para o dataclass."""
        return PublishedPost(
            id=str(post_model.id),
            titulo=post_model.title,
            resumo=post_model.excerpt,
            conteudo=post_model.content_markdown,
            data_criacao=post_model.created_at.isoformat(),
            data_atualizacao=post_model.updated_at.isoformat(),
            fonte="",  # O modelo Post não tem fonte, pode ser adicionado se necessário
            tags=[],  # Tags não são necessárias para detecção de duplicatas
            historico_atualizacoes=[]  # Será implementado quando o campo for adicionado ao modelo
        )

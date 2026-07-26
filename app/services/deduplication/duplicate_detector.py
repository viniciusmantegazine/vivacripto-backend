"""
Sistema de Detecção e Prevenção de Duplicatas
Orquestra o pipeline de verificação de similaridade e decisão
"""

import asyncio
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional
from datetime import datetime, timedelta, timezone
from enum import Enum
import json
from abc import ABC, abstractmethod
import uuid

from .similarity_engine import SimilarityFactory, SimilarityResult

# Usar logger centralizado do projeto
from app.core.logging import logger


class ActionType(Enum):
    """Tipos de ação possíveis"""
    CREATE_NEW = "criar"
    UPDATE_EXISTING = "atualizar"


@dataclass
class PostUpdate:
    """Registro de atualização de um post"""
    timestamp: str
    tipo_atualizacao: str  # "nova_informacao", "correcao", "complemento"
    conteudo_adicionado: str
    fonte: str
    resumo_mudancas: str


@dataclass
class PublishedPost:
    """Representa um post publicado no sistema"""
    id: str
    titulo: str
    resumo: str
    conteudo: str
    data_criacao: str
    data_atualizacao: str
    tags: List[str] = field(default_factory=list)
    fonte: str = ""
    historico_atualizacoes: List[PostUpdate] = field(default_factory=list)
    embedding_cache: Optional[str] = None
    
    def to_dict(self) -> Dict:
        """Converte para dicionário"""
        return {
            "id": self.id,
            "titulo": self.titulo,
            "resumo": self.resumo,
            "conteudo": self.conteudo,
            "data_criacao": self.data_criacao,
            "data_atualizacao": self.data_atualizacao,
            "tags": self.tags,
            "fonte": self.fonte,
            "historico_atualizacoes": [
                {
                    "timestamp": u.timestamp,
                    "tipo_atualizacao": u.tipo_atualizacao,
                    "conteudo_adicionado": u.conteudo_adicionado,
                    "fonte": u.fonte,
                    "resumo_mudancas": u.resumo_mudancas
                }
                for u in self.historico_atualizacoes
            ]
        }


@dataclass
class NewsAssignment:
    """Pauta de notícia para processar"""
    titulo: str
    resumo: str
    conteudo: str
    fonte: str
    timestamp: str
    id: Optional[str] = None

    def __post_init__(self):
        if self.id is None:
            self.id = str(uuid.uuid4())

    def get_combined_text(self, include_content: bool = True) -> str:
        """
        Retorna texto combinado para comparação de similaridade.

        Args:
            include_content: Se True, inclui os primeiros 500 chars do conteúdo
                           para comparação semântica mais precisa

        Returns:
            Texto combinado para análise de similaridade
        """
        base_text = f"{self.titulo} {self.resumo}"

        if include_content and self.conteudo:
            # Incluir primeiros 500 caracteres do conteúdo para melhor comparação semântica
            content_preview = self.conteudo[:500].strip()
            return f"{base_text} {content_preview}"

        return base_text


@dataclass
class DuplicateCheckResult:
    """Resultado da verificação de duplicata"""
    pauta_id: str
    acao: ActionType
    post_existente_id: Optional[str] = None
    similaridade_maxima: float = 0.0
    candidatos_similares: List[Dict] = field(default_factory=list)
    motivo: str = ""
    timestamp_verificacao: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict:
        """Converte para dicionário"""
        return {
            "pauta_id": self.pauta_id,
            "acao": self.acao.value,
            "post_existente_id": self.post_existente_id,
            "similaridade_maxima": round(self.similaridade_maxima, 4),
            "candidatos_similares": self.candidatos_similares,
            "motivo": self.motivo,
            "timestamp_verificacao": self.timestamp_verificacao
        }


class PostRepository(ABC):
    """Interface para repositório de posts"""
    
    @abstractmethod
    def get_posts_last_24h(self) -> List[PublishedPost]:
        """Retorna posts publicados nas últimas 24 horas"""
        pass
    
    @abstractmethod
    def get_post_by_id(self, post_id: str) -> Optional[PublishedPost]:
        """Retorna um post pelo ID"""
        pass
    
    @abstractmethod
    def save_post(self, post: PublishedPost) -> str:
        """Salva um novo post e retorna o ID"""
        pass
    
    @abstractmethod
    def update_post(self, post: PublishedPost) -> None:
        """Atualiza um post existente"""
        pass


class InMemoryPostRepository(PostRepository):
    """Implementação em memória do repositório (para testes)"""
    
    def __init__(self):
        self.posts: Dict[str, PublishedPost] = {}
    
    def get_posts_last_24h(self) -> List[PublishedPost]:
        """Retorna posts das últimas 24 horas"""
        cutoff_time = datetime.now() - timedelta(hours=24)
        result = []
        
        for post in self.posts.values():
            post_time = datetime.fromisoformat(post.data_criacao)
            if post_time >= cutoff_time:
                result.append(post)
        
        return result
    
    def get_post_by_id(self, post_id: str) -> Optional[PublishedPost]:
        """Retorna um post pelo ID"""
        return self.posts.get(post_id)
    
    def save_post(self, post: PublishedPost) -> str:
        """Salva um novo post"""
        if not post.id:
            post.id = str(uuid.uuid4())
        self.posts[post.id] = post
        logger.info(f"Post salvo: {post.id}")
        return post.id
    
    def update_post(self, post: PublishedPost) -> None:
        """Atualiza um post existente"""
        if post.id in self.posts:
            self.posts[post.id] = post
            logger.info(f"Post atualizado: {post.id}")
        else:
            raise ValueError(f"Post {post.id} não encontrado")


class DuplicateDetector:
    """
    Detector de duplicatas com verificação de similaridade
    Orquestra o pipeline de decisão
    """
    
    def __init__(
        self,
        repository: PostRepository,
        similarity_threshold: float = 0.80,
        engine_type: str = "hybrid"
    ):
        """
        Inicializa o detector

        Args:
            repository: Repositório de posts
            similarity_threshold: Threshold para considerar duplicata (padrão 80%)
            engine_type: Tipo de motor de similaridade
        """
        self.repository = repository
        self.similarity_threshold = similarity_threshold
        self.similarity_engine = SimilarityFactory.create(engine_type)
        self.engine_type = engine_type

        logger.info(
            f"DuplicateDetector inicializado: "
            f"engine={engine_type}, "
            f"threshold={similarity_threshold:.0%}"
        )
    
    async def check_duplicate(self, assignment: NewsAssignment) -> DuplicateCheckResult:
        """
        Verifica se uma pauta é duplicata de algum post existente
        
        Args:
            assignment: Pauta de notícia para verificar
        
        Returns:
            Resultado da verificação com ação recomendada
        """
        logger.info(f"Verificando pauta: {assignment.id}")
        
        # Buscar posts das últimas 24 horas
        recent_posts = await self.repository.get_posts_last_24h()
        
        if not recent_posts:
            logger.info("Nenhum post recente encontrado. Criando novo.")
            return DuplicateCheckResult(
                pauta_id=assignment.id,
                acao=ActionType.CREATE_NEW,
                motivo="Nenhum post publicado nas últimas 24 horas"
            )
        
        # Comparar com cada post recente (incluindo conteúdo para melhor precisão)
        assignment_text = assignment.get_combined_text(include_content=True)
        similarities = []

        for post in recent_posts:
            # Incluir conteúdo do post para comparação mais precisa
            post_content_preview = post.conteudo[:500] if post.conteudo else ""
            post_text = f"{post.titulo} {post.resumo} {post_content_preview}"
            
            try:
                # calculate() é CPU-bound síncrono (TF-IDF/embeddings): roda
                # fora do event loop para não bloquear as demais corrotinas.
                result = await asyncio.to_thread(
                    self.similarity_engine.calculate, assignment_text, post_text
                )
                similarities.append({
                    "post_id": post.id,
                    "titulo": post.titulo,
                    "similaridade": result.score,
                    "data_criacao": post.data_criacao,
                    "fonte": post.fonte
                })
                
                logger.debug(
                    f"Similaridade com '{post.titulo[:50]}': {result.score:.2%}"
                )
            except Exception as e:
                logger.error(f"Erro ao calcular similaridade: {e}")
                continue
        
        if not similarities:
            logger.warning("Erro ao calcular similaridades. Criando novo post.")
            return DuplicateCheckResult(
                pauta_id=assignment.id,
                acao=ActionType.CREATE_NEW,
                motivo="Erro ao calcular similaridades (fallback: criar novo)"
            )
        
        # Ordenar por similaridade
        similarities.sort(key=lambda x: x["similaridade"], reverse=True)
        max_similarity = similarities[0]["similaridade"]
        
        # Decidir ação baseado no threshold
        if max_similarity >= self.similarity_threshold:
            # Duplicata detectada - atualizar post existente
            existing_post_id = similarities[0]["post_id"]
            
            logger.warning(
                f"Duplicata detectada! "
                f"Similaridade: {max_similarity:.2%} "
                f"Post existente: {existing_post_id}"
            )
            
            return DuplicateCheckResult(
                pauta_id=assignment.id,
                acao=ActionType.UPDATE_EXISTING,
                post_existente_id=existing_post_id,
                similaridade_maxima=max_similarity,
                candidatos_similares=similarities[:3],
                motivo=f"Duplicata detectada com {max_similarity:.0%} de similaridade"
            )
        
        else:
            # Similaridade abaixo do threshold - criar novo post
            logger.info(
                f"Conteúdo diferente. "
                f"Similaridade máxima: {max_similarity:.2%}. "
                f"Criando novo post."
            )
            
            return DuplicateCheckResult(
                pauta_id=assignment.id,
                acao=ActionType.CREATE_NEW,
                similaridade_maxima=max_similarity,
                candidatos_similares=similarities[:3],
                motivo=f"Conteúdo suficientemente diferente (max: {max_similarity:.0%})"
            )

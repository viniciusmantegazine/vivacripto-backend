"""
Sistema de Detecção e Prevenção de Duplicatas
Orquestra o pipeline de verificação de similaridade e decisão
"""

from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from enum import Enum
import json
import logging
from abc import ABC, abstractmethod
import uuid

from .similarity_engine import SimilarityFactory, SimilarityResult

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ActionType(Enum):
    """Tipos de ação possíveis"""
    CREATE_NEW = "criar"
    UPDATE_EXISTING = "atualizar"
    REVIEW_MANUAL = "revisar_manualmente"


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
    
    def get_combined_text(self) -> str:
        """Retorna texto combinado para comparação"""
        return f"{self.titulo} {self.resumo}"


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
        engine_type: str = "hybrid",
        review_threshold: float = 0.60
    ):
        """
        Inicializa o detector
        
        Args:
            repository: Repositório de posts
            similarity_threshold: Threshold para considerar duplicata (padrão 80%)
            engine_type: Tipo de motor de similaridade
            review_threshold: Threshold para revisão manual (entre 60-80%)
        """
        self.repository = repository
        self.similarity_threshold = similarity_threshold
        self.review_threshold = review_threshold
        self.similarity_engine = SimilarityFactory.create(engine_type)
        self.engine_type = engine_type
        
        logger.info(
            f"DuplicateDetector inicializado: "
            f"engine={engine_type}, "
            f"threshold={similarity_threshold:.0%}, "
            f"review_threshold={review_threshold:.0%}"
        )
    
    def check_duplicate(self, assignment: NewsAssignment) -> DuplicateCheckResult:
        """
        Verifica se uma pauta é duplicata de algum post existente
        
        Args:
            assignment: Pauta de notícia para verificar
        
        Returns:
            Resultado da verificação com ação recomendada
        """
        logger.info(f"Verificando pauta: {assignment.id}")
        
        # Buscar posts das últimas 24 horas
        recent_posts = self.repository.get_posts_last_24h()
        
        if not recent_posts:
            logger.info("Nenhum post recente encontrado. Criando novo.")
            return DuplicateCheckResult(
                pauta_id=assignment.id,
                acao=ActionType.CREATE_NEW,
                motivo="Nenhum post publicado nas últimas 24 horas"
            )
        
        # Comparar com cada post recente
        assignment_text = assignment.get_combined_text()
        similarities = []
        
        for post in recent_posts:
            post_text = f"{post.titulo} {post.resumo}"
            
            try:
                result = self.similarity_engine.calculate(assignment_text, post_text)
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
        
        elif max_similarity >= self.review_threshold:
            # Similaridade intermediária - revisar manualmente
            logger.info(
                f"Similaridade intermediária detectada: {max_similarity:.2%}. "
                f"Requer revisão manual."
            )
            
            return DuplicateCheckResult(
                pauta_id=assignment.id,
                acao=ActionType.REVIEW_MANUAL,
                similaridade_maxima=max_similarity,
                candidatos_similares=similarities[:3],
                motivo=f"Similaridade intermediária ({max_similarity:.0%}). Requer revisão."
            )
        
        else:
            # Conteúdo suficientemente diferente - criar novo post
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
    
    def process_assignment(
        self,
        assignment: NewsAssignment
    ) -> Tuple[DuplicateCheckResult, Optional[PublishedPost]]:
        """
        Processa uma pauta completa: verifica duplicata e toma ação
        
        Args:
            assignment: Pauta de notícia
        
        Returns:
            Tupla (resultado_verificacao, post_criado_ou_atualizado)
        """
        # Verificar duplicata
        check_result = self.check_duplicate(assignment)
        
        if check_result.acao == ActionType.CREATE_NEW:
            # Criar novo post
            new_post = PublishedPost(
                id=str(uuid.uuid4()),
                titulo=assignment.titulo,
                resumo=assignment.resumo,
                conteudo=assignment.conteudo,
                data_criacao=assignment.timestamp,
                data_atualizacao=assignment.timestamp,
                fonte=assignment.fonte,
                tags=self._extract_tags(assignment)
            )
            
            self.repository.save_post(new_post)
            logger.info(f"Novo post criado: {new_post.id}")
            
            return check_result, new_post
        
        elif check_result.acao == ActionType.UPDATE_EXISTING:
            # Atualizar post existente
            existing_post = self.repository.get_post_by_id(
                check_result.post_existente_id
            )
            
            if existing_post is None:
                logger.error(
                    f"Post {check_result.post_existente_id} não encontrado"
                )
                return check_result, None
            
            # Adicionar atualização ao histórico
            update = PostUpdate(
                timestamp=datetime.now().isoformat(),
                tipo_atualizacao="nova_informacao",
                conteudo_adicionado=assignment.conteudo,
                fonte=assignment.fonte,
                resumo_mudancas=f"Atualizado com informação de {assignment.fonte}"
            )
            
            existing_post.historico_atualizacoes.append(update)
            existing_post.data_atualizacao = datetime.now().isoformat()
            
            # Complementar conteúdo se necessário
            if assignment.conteudo not in existing_post.conteudo:
                existing_post.conteudo += f"\n\n[Atualização - {assignment.fonte}]\n{assignment.conteudo}"
            
            self.repository.update_post(existing_post)
            logger.info(f"Post atualizado: {existing_post.id}")
            
            return check_result, existing_post
        
        else:
            # Revisão manual
            logger.warning(
                f"Pauta requer revisão manual: {assignment.id}"
            )
            return check_result, None
    
    @staticmethod
    def _extract_tags(assignment: NewsAssignment) -> List[str]:
        """Extrai tags da pauta (implementação simples)"""
        # Palavras-chave comuns em criptografia
        keywords = {
            "bitcoin": "Bitcoin",
            "ethereum": "Ethereum",
            "cripto": "Criptografia",
            "blockchain": "Blockchain",
            "nft": "NFT",
            "defi": "DeFi",
            "exchange": "Exchange",
            "moeda": "Moeda Digital",
            "regulação": "Regulação",
            "sec": "SEC",
            "banco": "Banco",
            "fintech": "Fintech"
        }
        
        combined_text = (
            assignment.titulo + " " + assignment.resumo
        ).lower()
        
        tags = []
        for keyword, tag in keywords.items():
            if keyword in combined_text:
                tags.append(tag)
        
        return list(set(tags))


class PipelineOrchestrator:
    """Orquestra o pipeline completo de processamento de notícias"""
    
    def __init__(
        self,
        detector: DuplicateDetector,
        auto_publish: bool = False
    ):
        """
        Inicializa o orquestrador
        
        Args:
            detector: Detector de duplicatas
            auto_publish: Se True, publica automaticamente posts aprovados
        """
        self.detector = detector
        self.auto_publish = auto_publish
        self.processing_log: List[Dict] = []
    
    def process_batch(self, assignments: List[NewsAssignment]) -> Dict:
        """
        Processa um lote de pautas
        
        Args:
            assignments: Lista de pautas para processar
        
        Returns:
            Resumo do processamento
        """
        logger.info(f"Processando lote de {len(assignments)} pautas")
        
        results = {
            "total": len(assignments),
            "criados": 0,
            "atualizados": 0,
            "revisao_manual": 0,
            "detalhes": []
        }
        
        for assignment in assignments:
            try:
                check_result, post = self.detector.process_assignment(assignment)
                
                results["detalhes"].append(check_result.to_dict())
                
                if check_result.acao == ActionType.CREATE_NEW:
                    results["criados"] += 1
                elif check_result.acao == ActionType.UPDATE_EXISTING:
                    results["atualizados"] += 1
                else:
                    results["revisao_manual"] += 1
                
            except Exception as e:
                logger.error(f"Erro ao processar pauta {assignment.id}: {e}")
                results["detalhes"].append({
                    "pauta_id": assignment.id,
                    "erro": str(e)
                })
        
        # Resumo
        logger.info(
            f"Lote processado: "
            f"{results['criados']} criados, "
            f"{results['atualizados']} atualizados, "
            f"{results['revisao_manual']} para revisão"
        )
        
        return results
    
    def get_processing_log(self) -> List[Dict]:
        """Retorna log de processamento"""
        return self.processing_log


# Exemplo de uso
if __name__ == "__main__":
    # Criar repositório em memória
    repo = InMemoryPostRepository()
    
    # Criar detector
    detector = DuplicateDetector(
        repository=repo,
        similarity_threshold=0.80,
        engine_type="hybrid"
    )
    
    # Criar orquestrador
    orchestrator = PipelineOrchestrator(detector)
    
    # Simular pautas
    assignments = [
        NewsAssignment(
            titulo="Bank of America e Coinbase anunciam parceria estratégica",
            resumo="Instituição financeira tradicional firma acordo com exchange de criptomoedas",
            conteudo="Bank of America e Coinbase anunciaram uma parceria estratégica...",
            fonte="CoinDesk",
            timestamp=datetime.now().isoformat()
        ),
        NewsAssignment(
            titulo="Coinbase e Bank of America firmam acordo histórico",
            resumo="Duas gigantes do setor financeiro se unem para criptomoedas",
            conteudo="Em um movimento que surpreendeu o mercado, Coinbase e Bank of America...",
            fonte="Bloomberg",
            timestamp=datetime.now().isoformat()
        ),
        NewsAssignment(
            titulo="Bitcoin atinge novo recorde acima de 100 mil dólares",
            resumo="Criptomoeda mais valiosa ultrapassa marca histórica",
            conteudo="Bitcoin atingiu hoje um novo recorde histórico...",
            fonte="Reuters",
            timestamp=datetime.now().isoformat()
        )
    ]
    
    # Processar lote
    print("\n" + "=" * 70)
    print("PROCESSAMENTO DE LOTE DE PAUTAS")
    print("=" * 70)
    
    results = orchestrator.process_batch(assignments)
    
    print("\n" + json.dumps(results, indent=2, ensure_ascii=False))

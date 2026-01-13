"""
Exemplo de API FastAPI para o Sistema de Detecção de Duplicatas
Demonstra como integrar o sistema em um serviço web
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import logging

from similarity_engine import SimilarityFactory
from duplicate_detector import (
    DuplicateDetector,
    NewsAssignment,
    PublishedPost,
    PostRepository,
    ActionType,
    InMemoryPostRepository
)

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Criar aplicação FastAPI
app = FastAPI(
    title="VivaCripto - Sistema de Detecção de Duplicatas",
    description="API para verificar e prevenir conteúdo duplicado",
    version="1.0.0"
)

# ============================================================================
# Modelos Pydantic
# ============================================================================

class PautaRequest(BaseModel):
    """Modelo de entrada para uma nova pauta"""
    titulo: str
    resumo: str
    conteudo: str
    fonte: str


class PostResponse(BaseModel):
    """Modelo de resposta para um post"""
    id: str
    titulo: str
    resumo: str
    data_criacao: str
    data_atualizacao: str


class VerificacaoResponse(BaseModel):
    """Modelo de resposta para verificação de duplicata"""
    pauta_id: str
    acao: str  # "criar", "atualizar", "revisar_manualmente"
    post_existente_id: Optional[str] = None
    similaridade_maxima: float
    motivo: str


class ProcessamentoBatchResponse(BaseModel):
    """Modelo de resposta para processamento em lote"""
    total: int
    criados: int
    atualizados: int
    revisao_manual: int
    detalhes: List[dict]


# ============================================================================
# Inicialização Global
# ============================================================================

# Em produção, substitua InMemoryPostRepository por sua implementação real
repository = InMemoryPostRepository()

detector = DuplicateDetector(
    repository=repository,
    similarity_threshold=0.80,
    engine_type="hybrid"
)

# ============================================================================
# Endpoints
# ============================================================================

@app.get("/health")
async def health_check():
    """Verifica a saúde da API"""
    return {
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "engine": detector.engine_type,
        "threshold": detector.similarity_threshold
    }


@app.post("/verificar", response_model=VerificacaoResponse)
async def verificar_duplicata(pauta: PautaRequest):
    """
    Verifica se uma pauta é duplicata de um post existente
    
    **Parâmetros:**
    - titulo: Título da notícia
    - resumo: Resumo ou descrição breve
    - conteudo: Conteúdo completo
    - fonte: Fonte da notícia (ex: CoinDesk, Bloomberg)
    
    **Retorno:**
    - acao: "criar", "atualizar", ou "revisar_manualmente"
    - similaridade_maxima: Score de similaridade (0-1)
    - motivo: Explicação da decisão
    """
    try:
        assignment = NewsAssignment(
            titulo=pauta.titulo,
            resumo=pauta.resumo,
            conteudo=pauta.conteudo,
            fonte=pauta.fonte,
            timestamp=datetime.now().isoformat()
        )
        
        result = detector.check_duplicate(assignment)
        
        return VerificacaoResponse(
            pauta_id=result.pauta_id,
            acao=result.acao.value,
            post_existente_id=result.post_existente_id,
            similaridade_maxima=round(result.similaridade_maxima, 4),
            motivo=result.motivo
        )
    
    except Exception as e:
        logger.error(f"Erro ao verificar duplicata: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/processar", response_model=ProcessamentoBatchResponse)
async def processar_lote(pautas: List[PautaRequest]):
    """
    Processa um lote de pautas
    
    **Parâmetros:**
    - Lista de pautas (máximo 100 por requisição)
    
    **Retorno:**
    - Resumo do processamento com contagem de ações
    """
    if len(pautas) > 100:
        raise HTTPException(
            status_code=400,
            detail="Máximo de 100 pautas por requisição"
        )
    
    try:
        assignments = [
            NewsAssignment(
                titulo=p.titulo,
                resumo=p.resumo,
                conteudo=p.conteudo,
                fonte=p.fonte,
                timestamp=datetime.now().isoformat()
            )
            for p in pautas
        ]
        
        from duplicate_detector import PipelineOrchestrator
        orchestrator = PipelineOrchestrator(detector)
        results = orchestrator.process_batch(assignments)
        
        return ProcessamentoBatchResponse(**results)
    
    except Exception as e:
        logger.error(f"Erro ao processar lote: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/posts/recentes")
async def listar_posts_recentes():
    """
    Lista os posts publicados nas últimas 24 horas
    
    **Retorno:**
    - Lista de posts com ID, título e data de criação
    """
    try:
        posts = repository.get_posts_last_24h()
        
        return {
            "total": len(posts),
            "posts": [
                {
                    "id": p.id,
                    "titulo": p.titulo,
                    "data_criacao": p.data_criacao,
                    "data_atualizacao": p.data_atualizacao,
                    "fonte": p.fonte
                }
                for p in posts
            ]
        }
    
    except Exception as e:
        logger.error(f"Erro ao listar posts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/posts/{post_id}")
async def obter_post(post_id: str):
    """
    Obtém detalhes de um post específico
    
    **Parâmetros:**
    - post_id: ID do post
    
    **Retorno:**
    - Detalhes completos do post, incluindo histórico de atualizações
    """
    try:
        post = repository.get_post_by_id(post_id)
        
        if not post:
            raise HTTPException(status_code=404, detail="Post não encontrado")
        
        return post.to_dict()
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao obter post: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/config")
async def obter_configuracao():
    """
    Obtém a configuração atual do detector
    
    **Retorno:**
    - Threshold de similaridade
    - Tipo de engine utilizado
    """
    return {
        "similarity_threshold": detector.similarity_threshold,
        "engine_type": detector.engine_type,
        "available_engines": ["levenshtein", "tfidf", "embedding", "hybrid"]
    }


@app.post("/config/threshold")
async def atualizar_threshold(novo_threshold: float):
    """
    Atualiza o threshold de similaridade
    
    **Parâmetros:**
    - novo_threshold: Novo valor entre 0.0 e 1.0
    """
    if not 0.0 <= novo_threshold <= 1.0:
        raise HTTPException(
            status_code=400,
            detail="Threshold deve estar entre 0.0 e 1.0"
        )
    
    detector.similarity_threshold = novo_threshold
    logger.info(f"Threshold atualizado para {novo_threshold}")
    
    return {
        "novo_threshold": novo_threshold,
        "mensagem": "Threshold atualizado com sucesso"
    }


# ============================================================================
# Exemplo de Uso
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    
    # Executar servidor
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
    
    # Após iniciar, você pode acessar:
    # - Documentação interativa: http://localhost:8000/docs
    # - Alternativa: http://localhost:8000/redoc

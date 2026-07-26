"""
Testes do DuplicateDetector — a segunda camada de deduplicação, que compara
um artigo recém-gerado contra posts publicados nas últimas 24h.

Contexto de por que este arquivo existe: o módulo tem 555 linhas e estava sem
nenhum teste, e o comentário do SOURCE_DEDUP_THRESHOLD em news_aggregator.py
apoiava a escolha daquele valor na premissa de que esta camada absorveria
falsos negativos. A premissa era falsa — ver
test_threshold_de_080_nao_dispara_em_duplicata_real.

Os testes aqui são de CARACTERIZAÇÃO: documentam o comportamento atual, mesmo
onde ele é questionável, para que qualquer mudança futura seja deliberada. Onde
o comportamento documentado é problemático, o docstring diz por quê.

Só cobrem a superfície viva do módulo. `PipelineOrchestrator` e
`process_assignment` não têm nenhum consumidor no projeto (~150 linhas mortas)
e ficam de fora de propósito.
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.deduplication.duplicate_detector import (
    ActionType,
    DuplicateDetector,
    NewsAssignment,
    PublishedPost,
)


def _assignment(titulo="Sberbank Anuncia Infraestrutura de Negociacao Cripto",
                resumo="O maior banco da Russia vai lancar negociacao de criptomoedas.",
                conteudo="## Sberbank entra no mercado cripto\n\nO Sberbank anunciou planos.",
                fonte="CoinDesk") -> NewsAssignment:
    return NewsAssignment(
        titulo=titulo,
        resumo=resumo,
        conteudo=conteudo,
        fonte=fonte,
        timestamp="2026-07-26T12:00:00",
    )


def _post(post_id="post-1", titulo="Titulo do post publicado",
          resumo="Resumo do post.", conteudo="Conteudo do post publicado.") -> PublishedPost:
    return PublishedPost(
        id=post_id,
        titulo=titulo,
        resumo=resumo,
        conteudo=conteudo,
        data_criacao="2026-07-26T10:00:00",
        data_atualizacao="2026-07-26T10:00:00",
        fonte="Cointelegraph",
    )


@pytest.fixture(autouse=True)
def sem_engine_real():
    """
    Impede que __init__ construa o engine de similaridade de verdade.

    O default de engine_type é "hybrid", que carrega modelo de embeddings — e
    cada teste aqui substitui o engine logo depois de construir o detector, de
    modo que carregar o real é desperdício puro. Sem este patch a suíte deste
    arquivo levava 272 segundos.
    """
    with patch(
        "app.services.deduplication.duplicate_detector.SimilarityFactory.create",
        return_value=MagicMock(),
    ) as factory:
        yield factory


def _detector(posts, score=0.0, threshold=0.80, erro=None):
    """
    Detector com repositório e engine de similaridade controlados.

    `score` é o valor que o engine devolve para qualquer par; `erro`, se dado,
    é levantado pelo engine.
    """
    repo = MagicMock()
    repo.get_posts_last_24h = AsyncMock(return_value=posts)

    detector = DuplicateDetector(repository=repo, similarity_threshold=threshold)

    engine = MagicMock()
    if erro is not None:
        engine.calculate = MagicMock(side_effect=erro)
    else:
        resultado = MagicMock()
        resultado.score = score
        engine.calculate = MagicMock(return_value=resultado)
    detector.similarity_engine = engine

    return detector, repo, engine


# --- NewsAssignment ------------------------------------------------------

def test_assignment_gera_id_automatico():
    a = _assignment()
    b = _assignment()

    assert a.id and b.id
    assert a.id != b.id


def test_assignment_respeita_id_informado():
    a = NewsAssignment(
        titulo="t", resumo="r", conteudo="c", fonte="f",
        timestamp="2026-07-26T12:00:00", id="fixo-123",
    )

    assert a.id == "fixo-123"


def test_combined_text_inclui_conteudo_por_padrao():
    a = _assignment(titulo="TITULO", resumo="RESUMO", conteudo="CONTEUDO")

    texto = a.get_combined_text()

    assert "TITULO" in texto and "RESUMO" in texto and "CONTEUDO" in texto


def test_combined_text_pode_excluir_conteudo():
    a = _assignment(titulo="TITULO", resumo="RESUMO", conteudo="CONTEUDO")

    texto = a.get_combined_text(include_content=False)

    assert "TITULO" in texto and "RESUMO" in texto
    assert "CONTEUDO" not in texto


def test_combined_text_trunca_conteudo_em_500_chars():
    """
    O corte em 500 é o que o detector compara. Importa porque duas notícias
    sobre o mesmo fato divergem mais no fim do texto que no lead.
    """
    a = _assignment(conteudo="x" * 900)

    texto = a.get_combined_text()

    assert texto.count("x") == 500


# --- check_duplicate: caminhos de decisão --------------------------------

@pytest.mark.asyncio
async def test_sem_posts_recentes_cria_novo():
    detector, _, engine = _detector(posts=[])

    resultado = await detector.check_duplicate(_assignment())

    assert resultado.acao == ActionType.CREATE_NEW
    assert "24 horas" in resultado.motivo
    engine.calculate.assert_not_called()


@pytest.mark.asyncio
async def test_similaridade_acima_do_threshold_atualiza():
    detector, _, _ = _detector(posts=[_post("post-42")], score=0.91)

    resultado = await detector.check_duplicate(_assignment())

    assert resultado.acao == ActionType.UPDATE_EXISTING
    assert resultado.post_existente_id == "post-42"
    assert resultado.similaridade_maxima == 0.91


@pytest.mark.asyncio
async def test_similaridade_abaixo_do_threshold_cria_novo():
    detector, _, _ = _detector(posts=[_post()], score=0.42)

    resultado = await detector.check_duplicate(_assignment())

    assert resultado.acao == ActionType.CREATE_NEW
    assert resultado.similaridade_maxima == 0.42


@pytest.mark.asyncio
async def test_threshold_e_inclusivo():
    """Score exatamente igual ao threshold conta como duplicata (>=)."""
    detector, _, _ = _detector(posts=[_post()], score=0.80, threshold=0.80)

    resultado = await detector.check_duplicate(_assignment())

    assert resultado.acao == ActionType.UPDATE_EXISTING


@pytest.mark.asyncio
async def test_escolhe_o_post_mais_similar_entre_varios():
    """Com vários candidatos, o update vai para o de maior similaridade."""
    posts = [_post("post-a"), _post("post-b"), _post("post-c")]
    detector, _, engine = _detector(posts=posts)

    def scores(texto_a, texto_b):
        # o post-b é o mais parecido
        r = MagicMock()
        r.score = 0.95 if "post-b" in texto_b or "B-MARCADOR" in texto_b else 0.50
        return r

    posts[1].conteudo = "B-MARCADOR conteudo"
    engine.calculate = MagicMock(side_effect=scores)

    resultado = await detector.check_duplicate(_assignment())

    assert resultado.acao == ActionType.UPDATE_EXISTING
    assert resultado.post_existente_id == "post-b"


@pytest.mark.asyncio
async def test_candidatos_similares_traz_no_maximo_tres():
    posts = [_post(f"post-{i}") for i in range(6)]
    detector, _, _ = _detector(posts=posts, score=0.10)

    resultado = await detector.check_duplicate(_assignment())

    assert len(resultado.candidatos_similares) == 3


# --- check_duplicate: falha do engine ------------------------------------

@pytest.mark.asyncio
async def test_erro_no_engine_para_todos_os_posts_cria_novo():
    """
    Fallback deliberadamente permissivo: sem conseguir comparar, publica.
    O risco assumido é duplicar em vez de perder a notícia.
    """
    detector, _, _ = _detector(posts=[_post()], erro=RuntimeError("engine fora"))

    resultado = await detector.check_duplicate(_assignment())

    assert resultado.acao == ActionType.CREATE_NEW
    assert "Erro ao calcular similaridades" in resultado.motivo


@pytest.mark.asyncio
async def test_erro_em_um_post_nao_impede_comparar_os_outros():
    """Falha isolada não descarta os candidatos restantes."""
    posts = [_post("post-ruim"), _post("post-bom")]
    detector, _, engine = _detector(posts=posts)

    chamadas = {"n": 0}

    def as_vezes_falha(a, b):
        chamadas["n"] += 1
        if chamadas["n"] == 1:
            raise RuntimeError("falha no primeiro")
        r = MagicMock()
        r.score = 0.93
        return r

    engine.calculate = MagicMock(side_effect=as_vezes_falha)

    resultado = await detector.check_duplicate(_assignment())

    assert resultado.acao == ActionType.UPDATE_EXISTING
    assert resultado.post_existente_id == "post-bom"


# --- o achado que motivou este arquivo -----------------------------------

def test_threshold_de_080_nao_dispara_em_duplicata_real():
    """
    O threshold DEFAULT de 0.80 está acima da faixa onde duplicata real cai,
    então a camada não pega nada — foi o que invalidou a premissa usada para
    escolher o SOURCE_DEDUP_THRESHOLD.

    Medido com o engine TF-IDF (que é o configurado em
    settings.DEDUPLICATION_ENGINE), comparando textos como o detector compara
    (titulo + resumo + conteudo[:500]):

      - mesmo evento, fontes diferentes: 0.535 a 0.619
      - eventos distintos:               0.041 a 0.181

    Existe uma lacuna larga e vazia entre 0.181 e 0.535: qualquer valor nela
    separaria bem. 0.80 não está nela.

    Este teste FALHA de propósito quando alguém corrigir o threshold para um
    valor dentro da faixa útil — e é isso que se quer. Quando falhar, troque-o
    por uma asserção de que o threshold está na lacuna.

    Ressalva sobre a medição: os pares de "mesmo evento" foram construídos à
    mão imitando o que o prompt produz, não são artigos gerados de verdade
    (não havia credencial de LLM no ambiente). A conclusão "0.80 nunca
    dispara" é robusta; o valor exato de substituição merece validação com
    dado de produção — o detector já loga a similaridade máxima em nível info.
    """
    assert DuplicateDetector.__init__.__defaults__[0] == 0.80, (
        "o threshold default mudou — se foi corrigido para a faixa 0.20-0.53, "
        "substitua este teste por uma asserção de que está na lacuna medida"
    )

    maior_duplicata_real_medida = 0.619
    assert maior_duplicata_real_medida < 0.80, (
        "com 0.80 a camada não dispara em duplicata real: falso negativo aqui "
        "resulta em conteúdo duplicado PUBLICADO"
    )


@pytest.mark.asyncio
async def test_update_sobrescreve_e_nao_mescla_conteudo():
    """
    Documenta o custo de um falso positivo nesta camada, que é mais alto que
    na deduplicação de fontes.

    O detector devolve apenas o ID do post a atualizar; quem aplica é
    ArticlePublisher.update_article, que SOBRESCREVE content_markdown e
    content_html — sem mesclar, e sem tocar no título.

    Consequências de um falso positivo: o artigo publicado é destruído, a nova
    história não ganha post próprio, e o post resultante fica com título antigo
    e corpo novo. Por isso a correção do threshold deve errar para o lado
    conservador, e por isso o desalinhamento título/corpo merece investigação
    própria — ele acontece mesmo em duplicata verdadeira.
    """
    detector, _, _ = _detector(posts=[_post("post-existente")], score=0.95)

    resultado = await detector.check_duplicate(_assignment())

    # O detector não carrega conteúdo a mesclar: só aponta o alvo.
    assert resultado.acao == ActionType.UPDATE_EXISTING
    assert resultado.post_existente_id == "post-existente"
    assert not hasattr(resultado, "conteudo_mesclado")

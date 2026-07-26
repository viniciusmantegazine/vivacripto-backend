"""
Testes do WeeklyReportGenerator.

Este arquivo nasceu de um bug: o serviço usava dois model IDs Claude
depreciados (primário E fallback), num endpoint vivo, sem nenhum teste que
avisasse. Os testes aqui cobrem o contrato da chamada à API — model IDs,
parâmetros aceitos, leitura da resposta e recusa — usando mocks, sem rede
e sem credencial.
"""
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.ai.weekly_report_generator import WeeklyReportGenerator

# IDs válidos na geração atual da API. Se um destes for depreciado, este
# teste falha e o aviso chega antes da produção.
MODELOS_ATUAIS = {"claude-opus-5", "claude-sonnet-5", "claude-opus-4-8"}


def test_model_ids_sao_da_geracao_atual():
    """Regressão: os IDs anteriores (claude-*-4-20250514) foram depreciados."""
    assert WeeklyReportGenerator.CLAUDE_MODEL in MODELOS_ATUAIS
    assert WeeklyReportGenerator.CLAUDE_FALLBACK_MODEL in MODELOS_ATUAIS


def test_nao_usa_ids_depreciados():
    """Guarda explícita contra os IDs que causaram o bug."""
    depreciados = {"claude-opus-4-20250514", "claude-sonnet-4-20250514"}
    assert WeeklyReportGenerator.CLAUDE_MODEL not in depreciados
    assert WeeklyReportGenerator.CLAUDE_FALLBACK_MODEL not in depreciados


class _Bloco:
    """Bloco de conteúdo estilo SDK Anthropic."""

    def __init__(self, tipo: str, **campos):
        self.type = tipo
        for nome, valor in campos.items():
            setattr(self, nome, valor)


class _Mensagem:
    """Resposta estilo SDK Anthropic."""

    def __init__(self, content, stop_reason="end_turn"):
        self.content = content
        self.stop_reason = stop_reason


def test_extract_text_ignora_bloco_de_thinking():
    """
    Regressão: com thinking ligado (padrão atual), content[0] é um bloco de
    thinking sem `.text` — o antigo content[0].text estourava AttributeError.
    """
    gen = WeeklyReportGenerator()
    mensagem = _Mensagem([
        _Bloco("thinking", thinking="raciocinio interno do modelo"),
        _Bloco("text", text="## Relatório\n\nConteúdo real."),
    ])

    assert gen._extract_text(mensagem) == "## Relatório\n\nConteúdo real."


def test_extract_text_com_texto_no_primeiro_bloco():
    """Sem thinking, o texto é o primeiro bloco — deve funcionar igual."""
    gen = WeeklyReportGenerator()
    mensagem = _Mensagem([_Bloco("text", text="  conteúdo  ")])

    assert gen._extract_text(mensagem) == "conteúdo"


def test_extract_text_sem_bloco_de_texto_retorna_none():
    """Resposta só com thinking (ou vazia) não é conteúdo — devolve None."""
    gen = WeeklyReportGenerator()

    assert gen._extract_text(_Mensagem([_Bloco("thinking", thinking="x")])) is None
    assert gen._extract_text(_Mensagem([])) is None


class _StreamFalso:
    """
    Context manager async que imita `client.messages.stream(...)`.

    Atenção: `stream()` NÃO é corrotina — devolve o context manager na hora.
    Por isso o mock que o retorna é MagicMock, não AsyncMock.
    """

    def __init__(self, mensagem):
        self._mensagem = mensagem

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def get_final_message(self):
        return self._mensagem


def _gerador_com_cliente(mensagens):
    """
    WeeklyReportGenerator com cliente Claude falso.

    `mensagens` é a lista de respostas a devolver, uma por chamada (permite
    testar o fallback). Um item que seja Exception é levantado.
    """
    gen = WeeklyReportGenerator()

    chamadas = []

    def stream(**kwargs):
        chamadas.append(kwargs)
        proxima = mensagens[len(chamadas) - 1]
        if isinstance(proxima, Exception):
            raise proxima
        return _StreamFalso(proxima)

    cliente = MagicMock()
    cliente.messages = MagicMock()
    cliente.messages.stream = MagicMock(side_effect=stream)

    gen.claude_client = cliente
    gen.claude_available = True
    return gen, chamadas


def _texto(conteudo="## Relatório\n\nCorpo do relatório."):
    return _Mensagem([_Bloco("text", text=conteudo)])


@pytest.fixture
def sem_rede(monkeypatch):
    """Neutraliza a coleta de dados de mercado (_generate_content faz rede)."""
    monkeypatch.setattr(
        "app.services.ai.market_data_collector.market_data_collector.collect_all",
        AsyncMock(return_value="dados de mercado de teste"),
    )


@pytest.mark.asyncio
async def test_nao_envia_parametros_removidos_pela_api(sem_rede):
    """
    Regressão crítica: `temperature` (e top_p/top_k) foram REMOVIDOS nos
    modelos atuais — enviá-los é HTTP 400.
    """
    gen, chamadas = _gerador_com_cliente([_texto()])

    await gen._generate_content()

    assert chamadas, "nenhuma chamada ao Claude foi feita"
    for kwargs in chamadas:
        assert "temperature" not in kwargs
        assert "top_p" not in kwargs
        assert "top_k" not in kwargs


@pytest.mark.asyncio
async def test_usa_streaming_e_teto_de_tokens_ampliado(sem_rede):
    """Streaming evita timeout; 16000 dá folga para thinking + texto longo."""
    gen, chamadas = _gerador_com_cliente([_texto()])

    await gen._generate_content()

    assert chamadas[0]["max_tokens"] == 16000
    assert chamadas[0]["model"] == WeeklyReportGenerator.CLAUDE_MODEL
    # É messages.stream que precisa ter sido chamado, não messages.create.
    # (MagicMock cria atributos sob demanda, então `messages.create` existiria
    # mesmo sem ser configurado — a asserção abaixo é o que prova o caminho.)
    gen.claude_client.messages.stream.assert_called()


def test_temperature_removida_das_constantes():
    """A constante TEMPERATURE não deve sobreviver ao refactor."""
    assert not hasattr(WeeklyReportGenerator, "TEMPERATURE")


@pytest.mark.asyncio
async def test_fallback_dispara_quando_primario_levanta(sem_rede):
    """Erro de rede/rate limit no primário deve cair no modelo de fallback."""
    gen, chamadas = _gerador_com_cliente([
        RuntimeError("500 overloaded"),
        _texto("## Relatório do fallback\n\nCorpo."),
    ])

    resultado = await gen._generate_content()

    assert resultado.startswith("## Relatório do fallback")
    assert chamadas[0]["model"] == WeeklyReportGenerator.CLAUDE_MODEL
    assert chamadas[1]["model"] == WeeklyReportGenerator.CLAUDE_FALLBACK_MODEL


def _recusa():
    """Recusa por classificador: HTTP 200, sem exceção, content vazio."""
    return _Mensagem([], stop_reason="refusal")


@pytest.mark.asyncio
async def test_recusa_no_primario_cai_para_o_fallback(sem_rede):
    """Classificadores diferem por modelo — vale tentar o fallback."""
    gen, chamadas = _gerador_com_cliente([
        _recusa(),
        _texto("## Relatório do fallback\n\nCorpo."),
    ])

    resultado = await gen._generate_content()

    assert resultado.startswith("## Relatório do fallback")
    assert len(chamadas) == 2


@pytest.mark.asyncio
async def test_recusa_nos_dois_modelos_retorna_none(sem_rede):
    """Recusa dupla não pode virar relatório vazio publicado como sucesso."""
    gen, _ = _gerador_com_cliente([_recusa(), _recusa()])

    assert await gen._generate_content() is None


@pytest.mark.asyncio
async def test_recusa_nao_e_confundida_com_texto_vazio(sem_rede):
    """
    Mesmo com bloco de texto presente, stop_reason=refusal invalida a
    resposta — o conteúdo é parcial e não deve ser publicado.
    """
    gen, _ = _gerador_com_cliente([
        _Mensagem([_Bloco("text", text="começo truncado")], stop_reason="refusal"),
        _recusa(),
    ])

    assert await gen._generate_content() is None

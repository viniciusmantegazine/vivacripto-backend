"""
Testes do sink JSON de producao.

O formato anterior montava JSON por interpolacao de string, entao qualquer
mensagem com aspas, barra invertida ou quebra de linha produzia uma linha que o
agregador nao parseava. Como titulo de noticia vai para o log, isso quebrava
justamente o caso que importa.

Nenhum teste toca rede ou disco: o sink escreve em stderr, que e capturado.
"""
import contextlib
import io
import json

import pytest
from loguru import logger

from app.core.logging import _json_sink, context_filter


def _emitir(acao) -> str:
    """Instala so o sink JSON, executa `acao`, devolve o que foi para stderr."""
    logger.remove()
    logger.add(_json_sink, level="INFO", filter=context_filter)
    buffer = io.StringIO()
    try:
        with contextlib.redirect_stderr(buffer):
            acao()
    finally:
        logger.remove()
    return buffer.getvalue()


def _payload(acao) -> dict:
    saida = _emitir(acao)
    assert saida.count("\n") == 1, f"esperava 1 linha, veio {saida.count(chr(10))}"
    return json.loads(saida)


# --- escape --------------------------------------------------------------

MENSAGENS_HOSTIS = [
    pytest.param('Trump: cripto e o "futuro do dinheiro"', id="aspas-duplas"),
    pytest.param(r"Path C:\Users\algo", id="barra-invertida"),
    pytest.param("Titulo\ncom quebra", id="quebra-de-linha"),
    pytest.param('a"b\\c\nd', id="os-tres-juntos"),
    pytest.param("Notícia de relevância", id="acento"),
]


@pytest.mark.parametrize("texto", MENSAGENS_HOSTIS)
def test_mensagem_hostil_sai_como_json_valido(texto):
    payload = _payload(lambda: logger.info(texto))

    assert payload["message"] == texto


def test_titulo_real_de_noticia_com_aspas_retas():
    """
    O caso que motivou o trabalho: titulo de noticia vira mensagem de log, e
    manchete com aspas retas quebrava a linha inteira.
    """
    titulo = 'Fora de tema: [Decrypt] Trump diz que cripto e o "futuro do dinheiro"'

    assert _payload(lambda: logger.info(titulo))["message"] == titulo


# --- contrato com o agregador --------------------------------------------

CAMPOS = (
    "timestamp",
    "level",
    "request_id",
    "correlation_id",
    "logger",
    "function",
    "line",
    "message",
)


def test_produz_exatamente_os_campos_do_contrato():
    """
    Os nomes de campo sao o contrato com o agregador de logs. Campo a mais ou a
    menos quebra query existente.
    """
    payload = _payload(lambda: logger.info("x"))

    assert set(payload) == set(CAMPOS)


def test_line_e_numero_e_nao_string():
    """O formato antigo emitia `"line":{line}` sem aspas. Tem de continuar assim."""
    payload = _payload(lambda: logger.info("x"))

    assert isinstance(payload["line"], int)


def test_timestamp_identico_ao_formato_antigo():
    """
    Trava a regressao mais facil de cometer: o formato antigo produz offset com
    dois-pontos (-03:00), e reconstruir com strftime("%z") daria -0300.
    """
    antigas = []
    logger.remove()
    logger.add(
        lambda m: antigas.append(str(m).rstrip()),
        format="{time:YYYY-MM-DDTHH:mm:ss.SSSZ}",
        level="INFO",
    )
    logger.add(_json_sink, level="INFO", filter=context_filter)
    buffer = io.StringIO()
    try:
        with contextlib.redirect_stderr(buffer):
            logger.info("y")
    finally:
        logger.remove()

    assert json.loads(buffer.getvalue())["timestamp"] == antigas[0]


# --- excecao -------------------------------------------------------------

def test_excecao_cabe_em_uma_linha_so():
    """
    Antes: `logger.exception` emitia a linha JSON e DEPOIS o traceback em
    linhas soltas, fora do objeto. O agregador via uma linha quebrada seguida
    de varias que nao eram JSON nenhum.
    """
    def falhar():
        try:
            raise ValueError('erro "citado"\ncom quebra')
        except Exception as e:
            logger.exception(f"Falhou: {e}")

    payload = _payload(falhar)

    assert payload["exception"].startswith("Traceback (most recent call last):")
    assert "ValueError" in payload["exception"]


def test_log_sem_excecao_nao_ganha_a_chave():
    assert "exception" not in _payload(lambda: logger.info("z"))


# --- o sink nao pode perder linha ----------------------------------------

class _Hostil:
    """Objeto que resiste a serializacao por qualquer caminho."""

    def __repr__(self):
        raise RuntimeError("nem repr funciona")

    def __str__(self):
        raise RuntimeError("nem str funciona")


class _Nivel:
    """Stub do objeto de nivel do loguru, que expõe `.name`."""

    name = "INFO"


class _MensagemFalsa:
    """Stub do objeto Message do loguru: o sink só lê `.record`."""

    def __init__(self, record):
        self.record = record


def _record_minimo(**sobrescreve) -> dict:
    from datetime import datetime, timezone

    record = {
        "time": datetime.now(timezone.utc),
        "level": _Nivel(),
        "extra": {"request_id": "-", "correlation_id": "-"},
        "name": "teste",
        "function": "f",
        "line": 1,
        "message": "msg",
        "exception": None,
    }
    record.update(sobrescreve)
    return record


def test_registro_nao_serializavel_ainda_produz_linha():
    """
    Sink que levanta faz o loguru escrever um bloco
    `--- Logging error in Loguru Handler ---` multi-linha em stderr — que e
    exatamente o tipo de saida nao parseavel que este trabalho elimina. Entao o
    sink degrada para uma linha minima em vez de deixar a excecao escapar.

    Chama `_json_sink` direto em vez de passar pelo logger: `context_filter`
    sobrescreve `extra["request_id"]` antes do sink rodar, entao um
    `logger.bind(request_id=...)` nunca chegaria ate aqui. Mudar o filtro para
    tornar o teste alcancavel seria alterar producao por causa de teste.
    """
    record = _record_minimo(extra={"request_id": _Hostil(), "correlation_id": "-"})
    buffer = io.StringIO()

    with contextlib.redirect_stderr(buffer):
        _json_sink(_MensagemFalsa(record))

    payload = json.loads(buffer.getvalue())
    assert payload["message"] == "falha ao serializar registro de log"
    assert "RuntimeError" in payload["sink_error"]


# --- fiacao em setup_logging ---------------------------------------------

def test_producao_usa_o_sink_json(monkeypatch):
    """
    Sem isto, a funcao existiria sem ninguem chama-la e o bug continuaria vivo
    em producao.
    """
    import app.core.logging as modulo

    monkeypatch.setattr(modulo.settings, "DEBUG", False)
    adicionados = []
    monkeypatch.setattr(
        modulo.logger, "add", lambda alvo, **kw: adicionados.append((alvo, kw))
    )
    monkeypatch.setattr(modulo.logger, "remove", lambda *a, **k: None)

    modulo.setup_logging()

    alvos = [alvo for alvo, _ in adicionados]
    assert modulo._json_sink in alvos, "o ramo de producao nao usa o sink JSON"


def test_producao_mantem_o_context_filter(monkeypatch):
    """
    E o context_filter que popula request_id e correlation_id no record. Sem
    ele os dois campos sumiriam do contrato com o agregador.
    """
    import app.core.logging as modulo

    monkeypatch.setattr(modulo.settings, "DEBUG", False)
    adicionados = []
    monkeypatch.setattr(
        modulo.logger, "add", lambda alvo, **kw: adicionados.append((alvo, kw))
    )
    monkeypatch.setattr(modulo.logger, "remove", lambda *a, **k: None)

    modulo.setup_logging()

    kwargs = next(kw for alvo, kw in adicionados if alvo is modulo._json_sink)
    assert kwargs.get("filter") is modulo.context_filter


def test_desenvolvimento_nao_usa_o_sink_json(monkeypatch):
    """O ramo de DEBUG e formato colorido para humano, nao JSON."""
    import app.core.logging as modulo

    monkeypatch.setattr(modulo.settings, "DEBUG", True)
    adicionados = []
    monkeypatch.setattr(
        modulo.logger, "add", lambda alvo, **kw: adicionados.append((alvo, kw))
    )
    monkeypatch.setattr(modulo.logger, "remove", lambda *a, **k: None)

    modulo.setup_logging()

    assert modulo._json_sink not in [alvo for alvo, _ in adicionados]


def test_context_filter_tem_precedencia_sobre_bind():
    """
    `context_filter` sobrescreve `extra["request_id"]` de proposito: o
    contextvar da requisicao e a fonte da verdade, e um `bind` de call site nao
    deve mascara-la. Este teste existe porque a alternativa (setdefault) parece
    inofensiva e muda a semantica.
    """
    payload = _payload(lambda: logger.bind(request_id="do-bind").info("x"))

    assert payload["request_id"] == "-"

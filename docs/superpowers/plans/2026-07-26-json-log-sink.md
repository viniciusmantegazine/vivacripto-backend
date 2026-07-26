# Sink JSON de Produção — Plano de Implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fazer o log JSON de produção sobreviver a aspas, barras invertidas e quebras de linha na mensagem.

**Architecture:** Trocar a format-string que monta JSON por interpolação por um sink callable que monta um `dict` e passa por `json.dumps`. Nomes de campo preservados exatamente. Traceback vai para um campo `exception` dentro do objeto em vez de linhas soltas fora dele.

**Tech Stack:** Python 3.9, `json` e `traceback` da stdlib, loguru, pytest. Sem dependência nova. Sem rede.

**Spec:** `docs/superpowers/specs/2026-07-26-json-log-sink-design.md`

---

## Código já validado

A função da Task 1 **não é rascunho** — foi prototipada e medida antes deste
plano existir. Resultado do protótipo:

| Verificação | Resultado |
|---|---|
| Aspas duplas, barra invertida, quebra de linha, os três juntos, acento | 1 linha, `json.loads` OK, `message` idêntico ao original nos 5 |
| Contrato de campos | exatamente as 8 chaves, sem extras, `line` é `int` |
| Timestamp vs. formato antigo | `2026-07-26T20:06:28.595-03:00` nos dois, igual |
| `logger.exception` | de ~6 linhas para **1**, com `exception` contendo o traceback |
| Sem exceção | chave `exception` ausente |
| `request_id` não serializável | fallback dispara, linha preservada e parseável |

## Duas armadilhas que o plano preserva

1. **Timestamp.** `isoformat(timespec="milliseconds")` produz `-03:00`.
   `strftime("%z")` produziria `-0300` — mudança silenciosa de contrato.
   Verificado byte a byte contra o formato antigo.
2. **`filter=context_filter` continua anexado.** É ele que popula
   `record["extra"]["request_id"]` e `["correlation_id"]`
   (`app/core/logging.py:43-47`). Sem ele os dois campos sumiriam.

---

## Estrutura de arquivos

| Arquivo | Responsabilidade |
|---|---|
| `app/core/logging.py` (modificar) | Ganha `_json_sink`; `setup_logging` passa a usá-lo no ramo de produção. |
| `tests/unit/test_json_log_sink.py` (criar) | Escape, contrato de campos, timestamp, exceção, fallback. |
| `ai_docs/gotchas.md` (modificar) | Registra por que não é format-string e por que não é `serialize=True`. |

---

### Task 1: A função `_json_sink`

**Files:**
- Modify: `app/core/logging.py`
- Test: `tests/unit/test_json_log_sink.py` (criar)

- [ ] **Step 1: Escrever os testes**

Criar `tests/unit/test_json_log_sink.py`:

```python
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


def test_registro_nao_serializavel_ainda_produz_linha():
    """
    Sink que levanta faz o loguru escrever um bloco
    `--- Logging error in Loguru Handler ---` multi-linha em stderr — que e
    exatamente o tipo de saida nao parseavel que este trabalho elimina. Entao o
    sink degrada para uma linha minima em vez de deixar a excecao escapar.
    """
    payload = _payload(lambda: logger.bind(request_id=_Hostil()).info("msg"))

    assert payload["message"] == "falha ao serializar registro de log"
    assert "RuntimeError" in payload["sink_error"]
```

- [ ] **Step 2: Rodar e verificar que falha**

Run: `python3 -m pytest tests/unit/test_json_log_sink.py -q`
Expected: FAIL — `ImportError: cannot import name '_json_sink' from 'app.core.logging'`

- [ ] **Step 3: Implementar o sink**

Em `app/core/logging.py`, trocar o bloco de imports do topo:

```python
import sys
from contextvars import ContextVar
from functools import wraps
from typing import Any, Callable, Dict, Optional
```

por:

```python
import json
import sys
import traceback as traceback_mod
from contextvars import ContextVar
from functools import wraps
from typing import Any, Callable, Dict, Optional
```

E acrescentar esta função logo após `context_filter` (antes de `setup_logging`):

```python
def _json_sink(message) -> None:
    """
    Escreve o record como UMA linha de JSON válido em stderr.

    Substitui a format-string que montava o JSON por interpolação. Aquela
    versão colocava `{message}` cru dentro de aspas, então qualquer mensagem
    com `"`, `\\` ou quebra de linha produzia linha que o agregador não
    parseava — e título de notícia vai para o log. `logger.exception` era pior:
    emitia o traceback em linhas soltas FORA do objeto JSON.

    Os nomes de campo são o contrato com o agregador e não podem mudar.
    Cuidado com dois detalhes:

    - `timestamp` usa `isoformat(timespec="milliseconds")` porque ele reproduz
      byte a byte o formato antigo `{time:YYYY-MM-DDTHH:mm:ss.SSSZ}`, que emite
      o offset COM dois-pontos (-03:00). `strftime("%z")` daria -0300.
    - `line` é número, não string. O formato antigo emitia `"line":{line}`.
    """
    record = message.record
    try:
        payload = {
            "timestamp": record["time"].isoformat(timespec="milliseconds"),
            "level": record["level"].name,
            "request_id": record["extra"].get("request_id", "-"),
            "correlation_id": record["extra"].get("correlation_id", "-"),
            "logger": record["name"],
            "function": record["function"],
            "line": record["line"],
            "message": record["message"],
        }

        exception = record["exception"]
        if exception is not None:
            payload["exception"] = "".join(
                traceback_mod.format_exception(
                    exception.type, exception.value, exception.traceback
                )
            ).rstrip()

        linha = json.dumps(payload, ensure_ascii=False, default=str)

    except Exception as e:
        # Deixar a exceção escapar faz o loguru escrever um bloco
        # `--- Logging error in Loguru Handler ---` multi-linha em stderr, que é
        # justamente a saída não parseável que este sink existe para eliminar.
        # Perder a estrutura de uma linha é aceitável; perder a linha não é.
        linha = json.dumps(
            {
                "timestamp": "-",
                "level": "ERROR",
                "request_id": "-",
                "correlation_id": "-",
                "logger": "app.core.logging",
                "function": "_json_sink",
                "line": 0,
                "message": "falha ao serializar registro de log",
                "sink_error": repr(e),
            }
        )

    sys.stderr.write(linha + "\n")
```

- [ ] **Step 4: Rodar e verificar que passa**

Run: `python3 -m pytest tests/unit/test_json_log_sink.py -q`
Expected: PASS, 12 passed (5 mensagens hostis + título real + campos + line + timestamp + exceção + sem-exceção + fallback).

- [ ] **Step 5: Rodar a suíte inteira**

Run: `python3 -m pytest tests/ -q`
Expected: PASS, 494 passed (baseline 482 + 12).

Se algum teste **pré-existente** quebrar, provavelmente é porque `_emitir`
chama `logger.remove()` e deixa o logger sem handler para os testes seguintes.
Investigue; a correção certa é o teste restaurar o estado, não relaxar a
asserção.

- [ ] **Step 6: Commit**

```bash
git add app/core/logging.py tests/unit/test_json_log_sink.py
git commit -m "feat(logging): sink JSON que escapa a mensagem corretamente"
```

---

### Task 2: Usar o sink em produção

Até aqui a função existe mas ninguém a usa. Esta task troca o handler.

**Files:**
- Modify: `app/core/logging.py:80-98`
- Test: `tests/unit/test_json_log_sink.py` (acrescentar)

- [ ] **Step 1: Escrever o teste de fiação**

Acrescentar ao fim de `tests/unit/test_json_log_sink.py`:

```python
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
```

- [ ] **Step 2: Rodar e verificar que falha**

Run: `python3 -m pytest tests/unit/test_json_log_sink.py -q`
Expected: FAIL em `test_producao_usa_o_sink_json` e `test_producao_mantem_o_context_filter` — o ramo de produção ainda usa a format-string.

- [ ] **Step 3: Trocar o handler de produção**

Em `app/core/logging.py`, substituir todo o bloco `else:` do `setup_logging`:

```python
    else:
        # Production: JSON format for log aggregation
        log_format = (
            '{{"timestamp":"{time:YYYY-MM-DDTHH:mm:ss.SSSZ}",'
            '"level":"{level}",'
            '"request_id":"{extra[request_id]}",'
            '"correlation_id":"{extra[correlation_id]}",'
            '"logger":"{name}",'
            '"function":"{function}",'
            '"line":{line},'
            '"message":"{message}"}}'
        )
        logger.add(
            sys.stderr,
            format=log_format,
            level="INFO",
            filter=context_filter,
            serialize=False,
        )
```

por:

```python
    else:
        # Produção: uma linha de JSON por registro, para o agregador.
        #
        # O sink monta um dict e passa por json.dumps em vez de interpolar numa
        # format-string. A versão anterior colocava {message} cru dentro de
        # aspas, então título de notícia com aspas retas quebrava a linha.
        # Ver _json_sink e ai_docs/gotchas.md.
        logger.add(
            _json_sink,
            level="INFO",
            filter=context_filter,
        )
```

- [ ] **Step 4: Rodar os testes do arquivo**

Run: `python3 -m pytest tests/unit/test_json_log_sink.py -q`
Expected: PASS, 15 passed (12 + 3 desta task).

- [ ] **Step 5: Rodar a suíte inteira**

Run: `python3 -m pytest tests/ -q`
Expected: PASS, 497 passed (482 + 15), sem nenhum teste pré-existente quebrado.

- [ ] **Step 6: Conferir a saída real de produção**

```bash
DEBUG=false python3 -c "
import sys; sys.path.insert(0,'.')
from app.core.logging import setup_logging
from loguru import logger
setup_logging()
logger.info('Fora de tema: [Decrypt] Trump diz que cripto e o \"futuro do dinheiro\"')
try:
    raise ValueError('erro \"citado\"')
except Exception as e:
    logger.exception(f'Falhou: {e}')
" 2>&1 | python3 -c "
import json, sys
for i, linha in enumerate(sys.stdin, 1):
    linha = linha.strip()
    if not linha: continue
    try:
        p = json.loads(linha)
        print(f'linha {i}: JSON valido | level={p[\"level\"]} | tem exception={\"exception\" in p}')
    except Exception as e:
        print(f'linha {i}: QUEBRADA -> {e}')
"
```

Expected: duas linhas, ambas `JSON valido`, a segunda com `tem exception=True`.
Se qualquer linha sair `QUEBRADA`, pare e reporte — é o bug que esta task
existe para eliminar.

- [ ] **Step 7: Commit**

```bash
git add app/core/logging.py tests/unit/test_json_log_sink.py
git commit -m "fix(logging): producao passa a usar o sink JSON"
```

---

### Task 3: Documentar

**Files:**
- Modify: `ai_docs/gotchas.md`

- [ ] **Step 1: Acrescentar a seção**

Acrescentar ao fim de `ai_docs/gotchas.md`:

```markdown
## Log JSON: nunca montar por format-string

O formato de produção em `app/core/logging.py` já montou JSON por interpolação:

    '"message":"{message}"}}'

`{message}` entrava cru dentro de aspas, então qualquer mensagem com `"`, `\` ou
quebra de linha produzia uma linha que o agregador não parseava. Título de
notícia vai para o log, e manchete com aspas retas é comum. `logger.exception`
era pior: emitia a linha JSON e **depois** o traceback em linhas soltas, fora do
objeto.

Na época havia 5 chamadas logando traceback completo (quebravam em 100% dos
casos), 76 interpolando texto de exceção e 418 chamadas de log no total.

Hoje o ramo de produção usa `_json_sink`, que monta um `dict` e passa por
`json.dumps`. Três coisas nele não são estéticas:

**Timestamp com `isoformat(timespec="milliseconds")`.** O formato antigo
`{time:YYYY-MM-DDTHH:mm:ss.SSSZ}` emite o offset COM dois-pontos (`-03:00`).
Reconstruir com `strftime("%z")` daria `-0300` — mudança silenciosa de contrato
com o agregador. Medido byte a byte.

**`line` é número, não string.** O formato antigo emitia `"line":{line}` sem
aspas.

**`filter=context_filter` continua anexado.** É ele que popula `request_id` e
`correlation_id` no record; sem ele os dois campos somem.

**Por que não `serialize=True`:** resolveria o escape, mas aninha tudo sob
`record` e move a mensagem, quebrando qualquer query existente no agregador. O
ganho não paga.

**O sink nunca deixa exceção escapar.** Se ele levantar, o loguru escreve um
bloco `--- Logging error in Loguru Handler ---` multi-linha em stderr — a mesma
saída não parseável que ele existe para eliminar. Por isso o corpo inteiro fica
em `try`/`except`, com um fallback que emite uma linha JSON mínima. Perder a
estrutura de uma linha é aceitável; perder a linha não é.

**Ainda em aberto:** `LogContext` e `log_operation` (mesmo arquivo) não são
usados em lugar nenhum do projeto, e o contexto estruturado que adicionam seria
descartado de qualquer forma — o sink só lê `request_id` e `correlation_id` de
`extra`. Decidir entre remover ou fazer funcionar.
```

- [ ] **Step 2: Commit**

```bash
git add ai_docs/gotchas.md
git commit -m "docs: registra por que o log JSON nao pode ser format-string"
```

---

## Encerramento

Após a Task 3, usar **superpowers:finishing-a-development-branch** na branch
`fix/json-log-sink`.

## O que este plano deliberadamente NÃO faz

- **Os 5 `logger.error(f"Traceback: {traceback.format_exc()}")`** em
  `news_pipeline.py` e `article_publisher.py`. Com o sink correto passam a
  produzir JSON válido sozinhos (o traceback vira string escapada em `message`).
  Continuam gerando duas linhas por erro em vez de uma; consolidar em
  `logger.exception` mudaria o padrão de grep e é decisão separada.
- **`LogContext` e `log_operation`.** Código não usado; remover ou ativar é
  outra decisão.
- **O sink de arquivo `logs/error.log`.** Texto puro, não sofre do problema.
- **Incluir `extra` inteiro no payload.** Aumentaria a linha e mudaria o
  contrato. Só `request_id` e `correlation_id` entram, como hoje.

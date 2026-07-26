# Migração dos modelos Claude do relatório semanal — Plano de Implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Corrigir os cinco defeitos que impedem o `WeeklyReportGenerator` de funcionar com modelos Claude atuais (IDs depreciados, `temperature` removido pela API, `max_tokens` dividido com thinking, leitura frágil de `content[0].text` e recusa não tratada), com cobertura de teste onde hoje há zero.

**Architecture:** As duas chamadas duplicadas ao Claude (primário e fallback) são extraídas para um único método `_call_claude(model, user_prompt)`. Isso é o que permite as cinco correções existirem em um lugar só — hoje qualquer conserto precisa ser aplicado duas vezes, que é exatamente como o problema se perpetuou. Um helper `_extract_text(message)` isola a leitura da resposta.

**Tech Stack:** Python 3.11+, SDK `anthropic` (AsyncAnthropic, streaming), pytest + pytest-asyncio, mocks (sem rede, sem credencial).

---

## Contexto essencial para o executor

- **Rodar testes:** `python3 -m pytest tests/unit/... -q` (não existe venv; use `python3`, não `python`).
- **Baseline (2026-07-26):** `321 passed, 0 failed, 0 errors`. Nenhum teste deve regredir. Se aparecer falha em `test_smart_image_generation.py`, ela é alheia a este plano — mas o esperado é zero.
- **Sem credencial Anthropic neste ambiente.** Não há `ANTHROPIC_API_KEY`, `.env` nem CLI `ant`. Todos os testes deste plano usam mocks. A validação de ponta a ponta do endpoint é pós-deploy.
- **Comentários de código em português** (convenção do projeto).
- **`WeeklyReportGenerator()` nasce desabilitado nos testes:** o construtor chama `_init_claude_client()`, que exige `settings.ANTHROPIC_API_KEY`. Sem a chave, `claude_available=False` e `claude_client=None`. Os testes injetam o cliente falso à mão (`gen.claude_client = fake; gen.claude_available = True`).
- **`_generate_content()` faz rede:** chama `market_data_collector.collect_all()`. Todo teste que exercite `_generate_content` precisa patchar isso, senão bate no CoinGecko de verdade.
- **Por que `content[0].text` é o defeito mais perigoso:** nos modelos atuais o thinking vem ligado por padrão, e blocos de thinking vêm **antes** do bloco de texto. `content[0]` passa a ser um `ThinkingBlock`, que não tem `.text` — `AttributeError` em produção.

---

### Task 1: Model IDs atuais

**Files:**
- Modify: `app/services/ai/weekly_report_generator.py:47-48`
- Test: `tests/unit/test_weekly_report_generator.py` (novo)

Contexto: `claude-opus-4-20250514` e `claude-sonnet-4-20250514` são IDs depreciados, com retirada documentada em 15/jun/2026. Primário e fallback são da mesma geração, então quando um falha por ID inválido o outro falha igual. O teste fixa os IDs atuais para que uma futura depreciação seja pega pela suíte, não em produção.

- [ ] **Step 1: Escrever o teste que falha**

Criar `tests/unit/test_weekly_report_generator.py`:

```python
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
```

- [ ] **Step 2: Rodar para confirmar que falha**

Run: `python3 -m pytest tests/unit/test_weekly_report_generator.py -q`
Expected: FAIL nos dois testes — `CLAUDE_MODEL` é `claude-opus-4-20250514`, que não está em `MODELOS_ATUAIS` e está em `depreciados`.

- [ ] **Step 3: Implementar**

Em `app/services/ai/weekly_report_generator.py`, substituir as linhas 46-48:

```python
    # Modelos Claude. IDs sem sufixo de data — não acrescentar um.
    # Os anteriores (claude-opus-4-20250514 / claude-sonnet-4-20250514) foram
    # depreciados com retirada em 15/jun/2026; primário e fallback eram da
    # mesma geração, então o fallback não salvava nada.
    CLAUDE_MODEL = "claude-opus-5"
    CLAUDE_FALLBACK_MODEL = "claude-sonnet-5"
```

- [ ] **Step 4: Rodar para confirmar que passa**

Run: `python3 -m pytest tests/unit/test_weekly_report_generator.py -q`
Expected: PASS (2 testes)

- [ ] **Step 5: Commit**

```bash
git add app/services/ai/weekly_report_generator.py tests/unit/test_weekly_report_generator.py
git commit -m "fix(report): troca model IDs Claude depreciados por claude-opus-5 e claude-sonnet-5"
```

---

### Task 2: `_extract_text` — leitura da resposta que sobrevive ao thinking

**Files:**
- Modify: `app/services/ai/weekly_report_generator.py` (novo método na classe)
- Test: `tests/unit/test_weekly_report_generator.py` (adicionar)

Contexto: o código lê `response.content[0].text`. Nos modelos atuais o thinking vem ligado por padrão e seus blocos vêm **antes** do texto, então `content[0]` é um `ThinkingBlock` sem atributo `.text` → `AttributeError`. Este helper é uma função pura sobre a mensagem, testável sem mockar stream.

- [ ] **Step 1: Escrever os testes que falham**

Adicionar ao final de `tests/unit/test_weekly_report_generator.py`:

```python
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
```

- [ ] **Step 2: Rodar para confirmar que falha**

Run: `python3 -m pytest tests/unit/test_weekly_report_generator.py -q`
Expected: FAIL com `AttributeError: 'WeeklyReportGenerator' object has no attribute '_extract_text'`

- [ ] **Step 3: Implementar**

Em `app/services/ai/weekly_report_generator.py`, adicionar o método na classe logo **antes** de `async def _generate_content` (linha 163):

```python
    def _extract_text(self, message) -> Optional[str]:
        """
        Extrai o texto da resposta do Claude.

        NÃO usar `message.content[0].text`: nos modelos atuais o thinking vem
        ligado por padrão e seus blocos vêm ANTES do texto, então o primeiro
        bloco não tem `.text` e o acesso direto estoura AttributeError.
        Varremos os blocos e pegamos o primeiro de tipo "text".
        """
        for block in message.content:
            if getattr(block, "type", None) == "text":
                return block.text.strip()
        return None
```

- [ ] **Step 4: Rodar para confirmar que passa**

Run: `python3 -m pytest tests/unit/test_weekly_report_generator.py -q`
Expected: PASS (5 testes)

- [ ] **Step 5: Commit**

```bash
git add app/services/ai/weekly_report_generator.py tests/unit/test_weekly_report_generator.py
git commit -m "fix(report): le o bloco de texto da resposta em vez de content[0] (quebra com thinking)"
```

---

### Task 3: `_call_claude` — streaming, `max_tokens` 16000 e remoção do `temperature`

**Files:**
- Modify: `app/services/ai/weekly_report_generator.py:51-52` (constantes), `163-239` (`_generate_content`)
- Test: `tests/unit/test_weekly_report_generator.py` (adicionar)

Contexto: três correções que mudam juntas a **forma da chamada**, por isso vêm numa task só — separá-las obrigaria a reescrever o mesmo harness de mock três vezes.

1. **`temperature=0.7` dá HTTP 400.** O parâmetro foi removido nos modelos atuais e não tem substituto. A intenção de tom migra para o prompt na Task 5.
2. **`max_tokens=8192` trunca.** O thinking agora divide esse teto com o texto; um relatório de 3000 palavras em português já consome ~4500 tokens sozinho.
3. **Streaming.** Requisição longa não-streaming estoura timeout de HTTP. `.get_final_message()` devolve a resposta completa no fim, então o resto do código não muda.

A extração de `_call_claude` é o coração da task: hoje o bloco de chamada está **duplicado** (linhas 204-211 e 224-231), e é por isso que os defeitos sobreviveram — todo conserto precisa ser feito em dois lugares.

- [ ] **Step 1: Escrever os testes que falham**

Adicionar ao final de `tests/unit/test_weekly_report_generator.py`:

```python
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
```

- [ ] **Step 2: Rodar para confirmar que falha**

Run: `python3 -m pytest tests/unit/test_weekly_report_generator.py -q`
Expected: FAIL nos 4 testes novos. O código ainda usa `messages.create`, que no cliente falso é um `MagicMock` auto-criado e não awaitable → `TypeError: object MagicMock can't be used in 'await' expression`. `test_temperature_removida_das_constantes` falha por `TEMPERATURE` ainda existir na classe.

- [ ] **Step 3: Implementar — constantes**

Substituir as linhas 50-52 de `app/services/ai/weekly_report_generator.py`:

```python
    # Configurações de geração.
    # 16000 e não 8192: nos modelos atuais o thinking vem ligado por padrão e
    # divide este teto com o texto da resposta. Um relatório de 3000 palavras
    # em português já consome ~4500 tokens sozinho.
    # NÃO reintroduzir `temperature`/`top_p`/`top_k`: foram removidos da API
    # nos modelos atuais e causam HTTP 400. O tom vive no system prompt.
    MAX_TOKENS = 16000
```

- [ ] **Step 4: Implementar — extrair `_call_claude`**

Adicionar o método logo **antes** de `_extract_text` (criado na Task 2):

```python
    async def _call_claude(self, model: str, user_prompt: str) -> Optional[str]:
        """
        Faz UMA chamada ao Claude e devolve o texto do relatório.

        Existe para desduplicar: o primário e o fallback tinham blocos de
        chamada idênticos, então cada correção precisava ser aplicada duas
        vezes — foi assim que os defeitos de parâmetro e de leitura da
        resposta sobreviveram.

        Usa streaming porque relatório longo + thinking é o caso clássico de
        requisição não-streaming estourar timeout de HTTP. `get_final_message`
        devolve a resposta completa, então quem chama não lida com eventos.

        Devolve None quando não há texto utilizável (sem levantar exceção).
        """
        async with self.claude_client.messages.stream(
            model=model,
            max_tokens=self.MAX_TOKENS,
            system=WEEKLY_REPORT_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        ) as stream:
            message = await stream.get_final_message()

        text = self._extract_text(message)
        if not text:
            logger.error(f"[Claude] {model} não retornou bloco de texto")
            return None
        return text
```

- [ ] **Step 5: Implementar — trocar o corpo duplicado**

Substituir o bloco inteiro que vai de `content = None` (logo após o `user_prompt`, ~linha 197) até o `return content` final de `_generate_content` (~linha 239) por:

```python
        # Primário; em falha ou resposta sem texto, tenta o fallback.
        try:
            logger.info(f"[Claude] Gerando relatório com {self.CLAUDE_MODEL}...")
            content = await self._call_claude(self.CLAUDE_MODEL, user_prompt)
            if content:
                logger.info(f"[Claude] Relatório gerado com sucesso ({len(content)} chars)")
                return content
            logger.warning("[Claude] Primário não produziu texto. Tentando fallback...")
        except Exception as e:
            logger.warning(f"[Claude] Falha no primário: {e}. Tentando fallback...")

        try:
            logger.info(f"[Claude] Tentando fallback com {self.CLAUDE_FALLBACK_MODEL}...")
            content = await self._call_claude(self.CLAUDE_FALLBACK_MODEL, user_prompt)
            if content:
                logger.info(f"[Claude Fallback] Relatório gerado com sucesso ({len(content)} chars)")
                return content
            logger.error("[Claude] Fallback também não produziu texto")
            return None
        except Exception as e2:
            logger.error(f"[Claude] Falha total na geração: {e2}")
            return None
```

- [ ] **Step 6: Rodar para confirmar que passa**

Run: `python3 -m pytest tests/unit/test_weekly_report_generator.py -q`
Expected: PASS (9 testes)

- [ ] **Step 7: Commit**

```bash
git add app/services/ai/weekly_report_generator.py tests/unit/test_weekly_report_generator.py
git commit -m "fix(report): remove temperature (HTTP 400), sobe max_tokens p/ thinking e adota streaming"
```

---

### Task 4: Tratamento de recusa por classificador

**Files:**
- Modify: `app/services/ai/weekly_report_generator.py` (`_call_claude`)
- Test: `tests/unit/test_weekly_report_generator.py` (adicionar)

Contexto: os modelos atuais podem recusar por classificador de segurança devolvendo **HTTP 200** com `stop_reason == "refusal"` e `content` vazio ou parcial — não é exceção, então o `try/except` não pega. Sem checagem, o código trata como sucesso e devolve relatório vazio.

Nota de comportamento: recusa no primário **cai para o fallback**, porque modelos diferentes têm classificadores diferentes e a segunda tentativa pode passar. Isso é uma melhoria sobre o spec (que previa `None` direto) e não custa nada: a lógica de fallback já existe.

- [ ] **Step 1: Escrever os testes que falham**

Adicionar ao final de `tests/unit/test_weekly_report_generator.py`:

```python
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
```

- [ ] **Step 2: Rodar para confirmar que falha**

Run: `python3 -m pytest tests/unit/test_weekly_report_generator.py -q`
Expected: FAIL — sem a checagem, `test_recusa_nao_e_confundida_com_texto_vazio` devolve `"começo truncado"` em vez de `None`.

- [ ] **Step 3: Implementar**

Em `_call_claude`, inserir a checagem entre o `get_final_message()` e a extração do texto:

```python
        async with self.claude_client.messages.stream(
            model=model,
            max_tokens=self.MAX_TOKENS,
            system=WEEKLY_REPORT_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        ) as stream:
            message = await stream.get_final_message()

        # Recusa por classificador vem como HTTP 200, não como exceção: o
        # try/except de quem chama não pega. Qualquer texto presente é
        # parcial e não deve ser publicado.
        if getattr(message, "stop_reason", None) == "refusal":
            logger.error(
                f"[Claude] {model} recusou a geração (classificador de segurança)"
            )
            return None

        text = self._extract_text(message)
```

- [ ] **Step 4: Rodar para confirmar que passa**

Run: `python3 -m pytest tests/unit/test_weekly_report_generator.py -q`
Expected: PASS (12 testes)

- [ ] **Step 5: Commit**

```bash
git add app/services/ai/weekly_report_generator.py tests/unit/test_weekly_report_generator.py
git commit -m "fix(report): trata recusa por classificador (HTTP 200) em vez de publicar vazio"
```

---

### Task 5: Instrução de tom que substitui o `temperature`

**Files:**
- Modify: `app/services/ai/prompts/weekly_report_prompts.py` — inserir antes da linha 259, que é o `"""` que fecha `WEEKLY_REPORT_SYSTEM_PROMPT` (a string começa na linha 6)
- Test: `tests/unit/test_weekly_report_prompts.py` (novo)

Contexto: o `temperature=0.7` existia para deixar a análise "um pouco mais criativa". O parâmetro não tem substituto na API atual, então a intenção precisa virar direção editorial explícita no prompt — senão o tom fica ao acaso. A última frase do bloco é deliberada: a diretriz de tom não pode abrir brecha nos guardrails de alucinação e de não-aconselhamento que o prompt já tem.

- [ ] **Step 1: Escrever os testes que falham**

Criar `tests/unit/test_weekly_report_prompts.py`:

```python
"""
Testes do system prompt do relatório semanal.

O parâmetro `temperature=0.7` foi removido (a API atual o rejeita com 400);
a intenção de "análise mais criativa" passou a viver no prompt. Estes testes
garantem que a diretriz existe e que ela não afrouxa os guardrails.
"""
from app.services.ai.prompts.weekly_report_prompts import WEEKLY_REPORT_SYSTEM_PROMPT


def test_tem_diretriz_de_voz_analitica():
    """Substitui o temperature removido — sem ela o tom fica ao acaso."""
    assert "<voz_analitica>" in WEEKLY_REPORT_SYSTEM_PROMPT
    assert "</voz_analitica>" in WEEKLY_REPORT_SYSTEM_PROMPT


def test_diretriz_de_tom_nao_afrouxa_os_guardrails():
    """
    A instrução de tom não pode virar licença para inventar dado ou dar
    conselho de investimento — ela reafirma os limites explicitamente.
    """
    inicio = WEEKLY_REPORT_SYSTEM_PROMPT.index("<voz_analitica>")
    fim = WEEKLY_REPORT_SYSTEM_PROMPT.index("</voz_analitica>")
    bloco = WEEKLY_REPORT_SYSTEM_PROMPT[inicio:fim].lower()

    assert "não inventar dados" in bloco
    assert "conselho de investimento" in bloco
    assert "prever preços" in bloco
```

- [ ] **Step 2: Rodar para confirmar que falha**

Run: `python3 -m pytest tests/unit/test_weekly_report_prompts.py -q`
Expected: FAIL — `<voz_analitica>` não existe no prompt (`AssertionError`, e `ValueError: substring not found` no segundo teste).

- [ ] **Step 3: Implementar**

Em `app/services/ai/prompts/weekly_report_prompts.py`, inserir o bloco imediatamente **antes** do `"""` que fecha `WEEKLY_REPORT_SYSTEM_PROMPT` (linha 259), depois do trecho "EXEMPLO DE FORMATAÇÃO CORRETA":

```

<voz_analitica>
Este é um relatório analítico, não um agregado de manchetes. Interprete o que
os dados da semana significam: conecte eventos que parecem separados, aponte
tensões entre sinais contraditórios e diga o que ainda não está claro.
Varie a construção das frases e evite estrutura repetitiva entre as seções.
Continuam valendo integralmente as regras de não inventar dados, não dar
conselho de investimento e não prever preços como fato.
</voz_analitica>
```

- [ ] **Step 4: Rodar para confirmar que passa**

Run: `python3 -m pytest tests/unit/test_weekly_report_prompts.py -q`
Expected: PASS (2 testes)

- [ ] **Step 5: Commit**

```bash
git add app/services/ai/prompts/weekly_report_prompts.py tests/unit/test_weekly_report_prompts.py
git commit -m "feat(report): diretriz de voz analitica no prompt substitui o temperature removido"
```

---

### Task 6: Verificação final

**Files:** nenhum (verificação)

- [ ] **Step 1: Suíte completa sem regressão**

Run: `python3 -m pytest tests/ -q 2>&1 | tail -3`
Expected: `335 passed, 0 failed, 0 errors` — baseline de 321 mais os 14 testes novos (12 em `test_weekly_report_generator.py` + 2 em `test_weekly_report_prompts.py`). Zero failed e zero errors.

- [ ] **Step 2: Confirmar que nenhum parâmetro removido sobrou no arquivo**

```bash
grep -n "temperature\|top_p\|top_k\|TEMPERATURE" app/services/ai/weekly_report_generator.py || echo "limpo ✓"
grep -n "content\[0\]\.text" app/services/ai/weekly_report_generator.py || echo "sem acesso direto a content[0] ✓"
grep -n "claude-opus-4-20250514\|claude-sonnet-4-20250514" app/ -r || echo "sem IDs depreciados ✓"
```
Expected: as três linhas de confirmação.

- [ ] **Step 3: Import limpo do serviço**

```bash
T=$(python3 -c "import secrets;print(secrets.token_urlsafe(32))"); \
SECRET_KEY=$T AUTOMATION_TOKEN=$T REVALIDATE_SECRET=$T \
DATABASE_URL="sqlite+aiosqlite:///:memory:" python3 -c "
from app.services.ai.weekly_report_generator import WeeklyReportGenerator
g = WeeklyReportGenerator()
print('modelo:', g.CLAUDE_MODEL, '| fallback:', g.CLAUDE_FALLBACK_MODEL)
print('max_tokens:', g.MAX_TOKENS)
print('tem TEMPERATURE?', hasattr(g, 'TEMPERATURE'))
"
```
Expected: `claude-opus-5` / `claude-sonnet-5`, `16000`, e `tem TEMPERATURE? False`.

- [ ] **Step 4: Verificação com credencial — PÓS-DEPLOY, não local**

Este ambiente não tem `ANTHROPIC_API_KEY`, `.env` nem CLI `ant`, então os passos abaixo **não rodam aqui**. Executar onde houver credencial:

```bash
python3 -c "
import anthropic
c = anthropic.Anthropic()
for mid in ('claude-opus-5', 'claude-sonnet-5'):
    m = c.models.retrieve(mid)
    print(mid, '->', m.display_name, '| max_output:', m.max_tokens)
"
```
Expected: os dois respondem. Depois, exercitar o endpoint de ponta a ponta:

```bash
curl -X POST "$BASE_URL/api/v1/automation/weekly-report" \
  -H "Authorization: Bearer $AUTOMATION_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"publish": false}'
```
Expected: relatório gerado com `word_count` entre 1500 e 3000. `publish: false` é preview e não persiste post.

- [ ] **Step 5: Nota de deploy**

Nenhuma migration, nenhuma env var nova, nenhuma dependência nova (`anthropic>=0.18.0` já está no `requirements.txt`; a versão instalada é 0.109.2). O deploy é só o código.

---

## Fora do escopo deste plano (deliberadamente adiado)

- **Parâmetro `fallbacks` server-side.** Dispara **só em recusa de política** — não em rate limit, overload ou erro de rede, que é o que o `try/except` cobre. Poderiam coexistir; não aqui.
- **Configurar `thinking` explicitamente.** O padrão dos modelos escolhidos (ligado, adaptativo) é o desejado para análise semanal.
- **`output_config.effort`.** Vale um experimento depois de estabilizar — pode reduzir custo sem perder qualidade — mas mexer em dois eixos ao mesmo tempo atrapalha a leitura do resultado.
- **Outros serviços de IA.** `content_generator.py` (Gemini/OpenAI) e `airdrop_post_generator.py` (`claude-sonnet-4-6`, ID atual e válido — verificado) não têm este problema.

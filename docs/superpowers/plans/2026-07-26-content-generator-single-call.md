# Consolidar as chamadas de LLM do ContentGenerator em uma — Plano de Implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Trocar as três chamadas de LLM de `generate_article` por uma só que devolve `content_markdown`, `title`, `excerpt` e `meta_description` num JSON — eliminando o descarte de artigo caro quando uma chamada acessória falha, e fazendo o `excerpt` ser escrito conforme especificação em vez de fatiado.

**Architecture:** Dois métodos novos com responsabilidades separadas: `_parse_article_json` (função pura sobre texto — cercas, `json.loads`, `json_repair`, validação de obrigatórios) e `_generate_article_json` (a chamada, com Gemini primário e OpenAI fallback). O contrato JSON vive no **prompt**, um só para os dois provedores; cada um recebe sua dica nativa de "responda JSON" como reforço. `generate_article` passa a orquestrar: uma chamada, parse, sanitização do conteúdo, fallback de excerpt, montagem do dict.

**Tech Stack:** Python 3.11+, `google-genai` 1.46.0 (`response_mime_type`), `openai` (`response_format`), `json_repair`, pytest.

---

## Contexto essencial para o executor

- **Rodar testes:** `python3 -m pytest tests/unit/... -q` (não existe venv; use `python3`).
- **Baseline (2026-07-26):** `353 passed, 0 failed, 0 errors`.
- **Comentários de código em português** (convenção do projeto).
- **Sem credencial de LLM neste ambiente.** Todo teste usa mock de cliente; nenhum toca a rede.
- **Por que uma chamada e não três:** hoje, se `_generate_seo_title` falha, `generate_article` retorna `None` e joga fora a chamada de conteúdo que já custou ~2500 tokens de saída. A decisão de não publicar sem título PT-BR está certa; o desenho de três chamadas é o que cria o dilema.
- **Duas faixas por campo, e elas não são a mesma coisa:** o prompt mira a faixa ideal de SEO (título 50–70, meta 140–160); o `QualityValidator` reprova fora da faixa absoluta (título 30–100, excerpt 80–200, meta 120–180). O prompt declara as duas — meta apertada como alvo, limite absoluto como fronteira.
- **`json_repair` não é luxo:** o modo de falha conhecido é o LLM não escapar aspas ou newlines dentro de um campo de markdown longo, que é exatamente o `content_markdown`. O `AirdropPostGenerator` já documenta isso.
- **Ordem das tasks evita quebra transitória:** as Tasks 1 e 2 **adicionam** métodos sem remover os antigos, então a suíte fica verde no meio do caminho. A Task 3 é o corte.

---

### Task 1: `_parse_article_json` — parse e validação de obrigatórios

**Files:**
- Modify: `app/services/ai/content_generator.py` — novo método na classe `ContentGenerator`
- Test: `tests/unit/test_content_generator_json_parse.py` (novo)

Função pura sobre texto: não chama LLM, não faz I/O. Por isso vem primeiro — é a peça mais fácil de testar e as outras dependem dela.

- [ ] **Step 1: Escrever os testes que falham**

Criar `tests/unit/test_content_generator_json_parse.py`:

```python
"""
Testes do _parse_article_json.

O LLM devolve o artigo inteiro num objeto JSON. O campo content_markdown é
longo e cheio de newlines e aspas, que é justamente onde modelos erram o
escape — por isso o parse tem json_repair como rede, e não só json.loads.

Obrigatórios são content_markdown e title: sem texto não há artigo, e sem
título PT-BR não publicamos (o fallback seria o título em inglês da fonte).
excerpt e meta_description são recuperáveis e NÃO invalidam o parse.
"""
import pytest

from app.services.ai.content_generator import ContentGenerator


@pytest.fixture
def generator() -> ContentGenerator:
    return ContentGenerator()


def _json_valido(**overrides) -> str:
    import json
    dados = {
        "content_markdown": "## Manchete\n\nCorpo do artigo.",
        "title": "Bitcoin Atinge Máxima Histórica Após Aprovação de ETF",
        "excerpt": "Bitcoin renova máxima em meio a forte demanda institucional por ETFs.",
        "meta_description": "Entenda o que a nova máxima do Bitcoin significa para o investidor brasileiro e o que observar adiante.",
    }
    dados.update(overrides)
    return json.dumps(dados)


def test_json_limpo_e_parseado(generator: ContentGenerator):
    resultado = generator._parse_article_json(_json_valido())

    assert resultado["title"].startswith("Bitcoin Atinge")
    assert resultado["content_markdown"].startswith("## Manchete")


def test_remove_cercas_de_codigo(generator: ContentGenerator):
    """Modelos frequentemente embrulham JSON em ```json ... ``` apesar do pedido."""
    resultado = generator._parse_article_json("```json\n" + _json_valido() + "\n```")

    assert resultado is not None
    assert resultado["title"].startswith("Bitcoin Atinge")


def test_json_repair_salva_aspas_nao_escapadas(generator: ContentGenerator):
    """
    Modo de falha conhecido: aspas cruas dentro do content_markdown longo.
    json.loads quebra; json_repair conserta sem desfigurar o conteúdo.
    """
    quebrado = (
        '{"content_markdown": "## Manchete\\n\\nO CEO disse "vamos crescer" ontem.",'
        ' "title": "Bitcoin Atinge Máxima Histórica Após Aprovação de ETF",'
        ' "excerpt": "Bitcoin renova máxima em meio a forte demanda institucional.",'
        ' "meta_description": "Entenda o que a máxima do Bitcoin significa para o investidor brasileiro hoje."}'
    )

    resultado = generator._parse_article_json(quebrado)

    assert resultado is not None
    assert "Manchete" in resultado["content_markdown"]


def test_texto_nao_json_retorna_none(generator: ContentGenerator):
    assert generator._parse_article_json("desculpe, não consigo ajudar com isso") is None


def test_vazio_retorna_none(generator: ContentGenerator):
    assert generator._parse_article_json("") is None
    assert generator._parse_article_json(None) is None


@pytest.mark.parametrize("campo", ["content_markdown", "title"])
def test_campo_obrigatorio_ausente_retorna_none(generator: ContentGenerator, campo: str):
    """Sem conteúdo ou sem título não há artigo publicável."""
    import json
    dados = json.loads(_json_valido())
    del dados[campo]

    assert generator._parse_article_json(json.dumps(dados)) is None


@pytest.mark.parametrize("campo", ["content_markdown", "title"])
def test_campo_obrigatorio_vazio_retorna_none(generator: ContentGenerator, campo: str):
    """String vazia ou só espaço é o mesmo que ausente."""
    assert generator._parse_article_json(_json_valido(**{campo: "   "})) is None


@pytest.mark.parametrize("campo", ["excerpt", "meta_description"])
def test_campo_recuperavel_ausente_nao_invalida(generator: ContentGenerator, campo: str):
    """
    excerpt tem fallback mecânico e meta_description é reparada pelo retry do
    pipeline. Descartar o artigo por causa deles repetiria justamente o defeito
    que esta consolidação existe para corrigir.
    """
    import json
    dados = json.loads(_json_valido())
    del dados[campo]

    resultado = generator._parse_article_json(json.dumps(dados))

    assert resultado is not None
    assert resultado.get(campo) is None
```

- [ ] **Step 2: Rodar para confirmar que falham**

Run: `python3 -m pytest tests/unit/test_content_generator_json_parse.py -q`
Expected: FAIL nos 11 testes com `AttributeError: 'ContentGenerator' object has no attribute '_parse_article_json'`

- [ ] **Step 3: Implementar**

Em `app/services/ai/content_generator.py`, adicionar o import no topo (junto aos outros imports de terceiros, depois de `from slugify import slugify`):

```python
import json

import json_repair
```

Adicionar as constantes na classe `ContentGenerator`, logo após `CASE_SENSITIVE_SITE_NAMES`:

```python
    # Campos que o LLM precisa entregar para o artigo existir. excerpt e
    # meta_description ficam de fora de propósito: são recuperáveis, e
    # descartar um artigo de 2500 tokens por causa deles repetiria o defeito
    # que esta consolidação corrige.
    REQUIRED_ARTICLE_FIELDS = ("content_markdown", "title")
```

Adicionar o método, logo antes de `_sanitize_content`:

```python
    def _parse_article_json(self, text: Optional[str]) -> Optional[Dict]:
        """
        Parseia o JSON do artigo devolvido pelo LLM.

        Duas defesas, nesta ordem:
        1. Remoção de cercas ```json — modelos embrulham mesmo quando o prompt
           pede JSON puro.
        2. json_repair quando json.loads falha. O caso comum é aspas ou
           newlines não escapadas dentro do content_markdown longo; o repair
           conserta sem desfigurar conteúdo válido.

        Devolve None quando não há JSON aproveitável ou quando falta campo
        obrigatório (REQUIRED_ARTICLE_FIELDS).
        """
        if not text:
            return None

        limpo = text.strip()
        if limpo.startswith("```"):
            partes = limpo.split("```")
            limpo = partes[1] if len(partes) > 1 else limpo
            if limpo.startswith("json"):
                limpo = limpo[4:]
            limpo = limpo.strip()

        dados = None
        try:
            dados = json.loads(limpo)
        except (json.JSONDecodeError, ValueError):
            try:
                dados = json_repair.loads(limpo)
            except Exception as e:
                logger.error(f"[JSON] Parse falhou mesmo com json_repair: {e}")
                return None

        if not isinstance(dados, dict):
            logger.error(f"[JSON] Esperado objeto, recebido {type(dados).__name__}")
            return None

        for campo in self.REQUIRED_ARTICLE_FIELDS:
            valor = dados.get(campo)
            if not isinstance(valor, str) or not valor.strip():
                logger.error(f"[JSON] Campo obrigatório ausente ou vazio: {campo}")
                return None

        return dados
```

- [ ] **Step 4: Rodar para confirmar que passam**

Run: `python3 -m pytest tests/unit/test_content_generator_json_parse.py -q`
Expected: PASS (11 testes — 5 simples e 3 parametrizados de 2 casos cada)

- [ ] **Step 5: Commit**

```bash
git add app/services/ai/content_generator.py tests/unit/test_content_generator_json_parse.py
git commit -m "feat(ai): _parse_article_json com json_repair e validacao de obrigatorios"
```

---

### Task 2: `_generate_article_json` — a chamada única

**Files:**
- Modify: `app/services/ai/content_generator.py` — novo método
- Test: `tests/unit/test_content_generator_single_call.py` (novo)
- Test: `tests/unit/test_content_generator_sanitize.py` — reescrever 2 testes de `correction_hint`

O método antigo `_generate_content` **continua existindo** nesta task; `generate_article` ainda o usa. Isso mantém a suíte verde e concentra o corte na Task 3.

- [ ] **Step 1: Escrever os testes que falham**

Criar `tests/unit/test_content_generator_single_call.py`:

```python
"""
Testes da chamada única de geração.

Antes: três chamadas sequenciais (conteúdo, título SEO, meta description).
Se a segunda falhava, o artigo inteiro era descartado junto com a chamada de
conteúdo que já custara ~2500 tokens de saída. Agora é uma transação: ou vem
tudo, ou não vem nada.
"""
import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.ai.content_generator import ContentGenerator

ARTIGO_JSON = json.dumps({
    "content_markdown": "## Manchete\n\n" + "palavra de conteudo " * 60,
    "title": "Bitcoin Atinge Máxima Histórica Após Aprovação de ETF",
    "excerpt": "Bitcoin renova máxima em meio a forte demanda institucional por ETFs listados.",
    "meta_description": "Entenda o que a nova máxima do Bitcoin significa para o investidor brasileiro e o que observar adiante.",
})


def _gerador_gemini(resposta_texto=ARTIGO_JSON, erro=None):
    """ContentGenerator com Gemini falso. Devolve (gen, chamadas)."""
    gen = ContentGenerator()
    chamadas = []

    async def generate_content(**kwargs):
        chamadas.append(kwargs)
        if erro is not None:
            raise erro
        resp = MagicMock()
        resp.text = resposta_texto
        return resp

    cliente = MagicMock()
    cliente.aio = MagicMock()
    cliente.aio.models = MagicMock()
    cliente.aio.models.generate_content = AsyncMock(side_effect=generate_content)

    gen.gemini_client = cliente
    gen.use_gemini = True
    return gen, chamadas


def _com_openai(gen, resposta_texto=ARTIGO_JSON):
    """Instala um cliente OpenAI falso e devolve a lista de chamadas."""
    chamadas = []

    async def create(**kwargs):
        chamadas.append(kwargs)
        msg = MagicMock()
        msg.message.content = resposta_texto
        resp = MagicMock()
        resp.choices = [msg]
        return resp

    gen.openai_client = MagicMock()
    gen.openai_client.chat = MagicMock()
    gen.openai_client.chat.completions = MagicMock()
    gen.openai_client.chat.completions.create = AsyncMock(side_effect=create)
    return chamadas


@pytest.mark.asyncio
async def test_faz_uma_unica_chamada():
    """O ponto central da consolidação: 1 chamada, não 3."""
    gen, chamadas = _gerador_gemini()

    resultado = await gen._generate_article_json(
        "Bitcoin Hits High", "texto da fonte", "CoinDesk", "bitcoin", None
    )

    assert resultado is not None
    assert len(chamadas) == 1


@pytest.mark.asyncio
async def test_pede_json_nativo_ao_gemini():
    """response_mime_type é o reforço nativo do contrato que vive no prompt."""
    gen, chamadas = _gerador_gemini()

    await gen._generate_article_json("t", "d", "s", "bitcoin", None)

    config = chamadas[0]["config"]
    assert config.response_mime_type == "application/json"


@pytest.mark.asyncio
async def test_contrato_dos_quatro_campos_esta_no_prompt():
    gen, chamadas = _gerador_gemini()

    await gen._generate_article_json("t", "d", "s", "bitcoin", None)

    prompt = chamadas[0]["contents"]
    for campo in ("content_markdown", "title", "excerpt", "meta_description"):
        assert campo in prompt, f"campo {campo} ausente do contrato no prompt"


@pytest.mark.asyncio
async def test_correction_hint_entra_no_prompt():
    """
    Em retry pós-reprovação o hint precisa chegar ao modelo. Substitui o teste
    equivalente que apontava para _generate_content.
    """
    gen, chamadas = _gerador_gemini()

    await gen._generate_article_json(
        "t", "d", "s", "bitcoin", "word count abaixo do minimo"
    )

    assert "word count abaixo do minimo" in chamadas[0]["contents"]


@pytest.mark.asyncio
async def test_sem_hint_nao_injeta_bloco_de_correcao():
    gen, chamadas = _gerador_gemini()

    await gen._generate_article_json("t", "d", "s", "bitcoin", None)

    assert "<correcao_obrigatoria>" not in chamadas[0]["contents"]


@pytest.mark.asyncio
async def test_fallback_openai_quando_gemini_falha():
    """Mesmo contrato nos dois provedores — é por isso que ele vive no prompt."""
    gen, chamadas_gemini = _gerador_gemini(erro=RuntimeError("429 rate limit"))
    chamadas_openai = _com_openai(gen)

    resultado = await gen._generate_article_json("t", "d", "s", "bitcoin", None)

    assert resultado is not None
    assert resultado["title"].startswith("Bitcoin Atinge")
    assert len(chamadas_gemini) == 1
    assert len(chamadas_openai) == 1
    assert chamadas_openai[0]["response_format"] == {"type": "json_object"}


@pytest.mark.asyncio
async def test_resposta_nao_json_retorna_none():
    gen, _ = _gerador_gemini(resposta_texto="desculpe, não posso ajudar")
    _com_openai(gen, resposta_texto="também não")

    assert await gen._generate_article_json("t", "d", "s", "bitcoin", None) is None
```

- [ ] **Step 2: Rodar para confirmar que falham**

Run: `python3 -m pytest tests/unit/test_content_generator_single_call.py -q`
Expected: FAIL nos 7 testes com `AttributeError: 'ContentGenerator' object has no attribute '_generate_article_json'`

- [ ] **Step 3: Implementar — o bloco do contrato JSON**

Em `app/services/ai/content_generator.py`, adicionar a constante na classe, logo após `REQUIRED_ARTICLE_FIELDS`:

```python
    # Contrato de saída. As faixas têm dois níveis: a meta apertada é o ponto
    # ideal de SEO, o limite absoluto é a fronteira em que o QualityValidator
    # reprova. Declarar os dois evita que o modelo mire no limite e resvale.
    JSON_CONTRACT_BLOCK = """
<saida_json>
Responda APENAS com um objeto JSON válido. Sem cercas de código, sem texto antes ou depois.

{{
  "content_markdown": "o artigo completo em Markdown, começando por ##",
  "title": "título SEO",
  "excerpt": "resumo curto do artigo",
  "meta_description": "meta description SEO"
}}

REGRAS DE CADA CAMPO:

content_markdown — o artigo conforme <estrutura_do_artigo> e <requisitos_tecnicos> acima.
  ⚠️ Escape corretamente as quebras de linha (\\n) e as aspas (\\") dentro da string JSON.

title — alvo 50 a 70 caracteres (limite absoluto: 30 a 100).
  - Inclua "{keyword}" preferencialmente no início ou meio
  - Atrativo, mas NUNCA clickbait sensacionalista
  - Verbos de ação quando apropriado (Revela, Anuncia, Lança, Atinge, Supera)
  - Português brasileiro fluente
  ✅ BONS: "Bitcoin Atinge Máxima Histórica Após Aprovação de ETF nos EUA" /
     "Ethereum Anuncia Data do Upgrade Dencun: O Que Muda Para Usuários" /
     "SEC Processa Binance por Irregularidades: Entenda o Caso"
  ❌ RUINS: "URGENTE: Bitcoin VAI EXPLODIR! Não Perca!!!" (clickbait) /
     "Notícia importante sobre Bitcoin" (genérico) /
     "Você não vai acreditar no que aconteceu com o Ethereum" (clickbait)

excerpt — alvo 120 a 180 caracteres (limite absoluto: 80 a 200).
  - Resuma a notícia em 1 ou 2 frases COMPLETAS
  - Não repita o título literalmente
  - NUNCA termine no meio de uma frase

meta_description — alvo 140 a 160 caracteres (limite absoluto: 120 a 180).
  - Inclua "{keyword}" de forma natural
  - Resuma o VALOR do artigo para o leitor
  - Termine com curiosidade ou CTA implícito (sem "clique aqui")
  - Complemente o título, não repita
  ✅ BOAS: "Entenda como a aprovação do ETF de Bitcoin nos EUA pode impactar o
     mercado cripto brasileiro e o que esperar nos próximos meses."
  ❌ RUINS: "Leia nossa notícia sobre Bitcoin. Clique aqui para saber mais."
     (genérico, CTA explícito) / "Bitcoin Bitcoin criptomoeda crypto blockchain"
     (keyword stuffing)
</saida_json>"""
```

- [ ] **Step 4: Implementar — o método**

Adicionar logo antes de `_parse_article_json`:

```python
    async def _generate_article_json(
        self,
        title: str,
        description: str,
        source: str,
        category: str = "default",
        correction_hint: Optional[str] = None,
    ) -> Optional[Dict]:
        """
        Gera o artigo completo — conteúdo, título, excerpt e meta — numa
        chamada só.

        Antes eram três chamadas sequenciais, e uma falha na segunda descartava
        o artigo junto com a chamada de conteúdo já paga. Aqui é transação
        única: ou vem tudo, ou não vem nada.

        O contrato JSON vive no PROMPT, não no mecanismo de saída estruturada
        de cada provedor: Gemini e OpenAI têm mecanismos diferentes, e apostar
        neles exigiria duas implementações de contrato. Cada provedor recebe
        apenas sua dica nativa de "responda JSON" como reforço barato.
        """
        cat_config = self._get_category_config(category)
        keyword = cat_config["keywords"][0] if cat_config["keywords"] else "criptomoeda"

        user_prompt = self._build_article_prompt(
            title, description, source, category, keyword, correction_hint
        )
        full_prompt = f"{self.SYSTEM_PROMPT}\n\n{user_prompt}"

        # Gemini primário
        if self.use_gemini and self.gemini_client:
            try:
                logger.info(f"[Gemini] Gerando artigo (chamada única) com {self.GEMINI_MODEL}...")
                response = await self.gemini_client.aio.models.generate_content(
                    model=self.GEMINI_MODEL,
                    contents=full_prompt,
                    config=genai.types.GenerateContentConfig(
                        temperature=0.4,
                        response_mime_type="application/json",
                    ),
                )
                artigo = self._parse_article_json(getattr(response, "text", None))
                if artigo:
                    return artigo
                logger.warning("[Gemini] JSON inaproveitável. Tentando OpenAI...")
            except Exception as e:
                logger.warning(f"[Gemini] Falha: {e}. Tentando OpenAI...")

        # Fallback OpenAI, mesmo contrato
        try:
            logger.info(f"[OpenAI] Gerando artigo (chamada única) com {self.OPENAI_MODEL}...")
            response = await self.openai_client.chat.completions.create(
                model=self.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.4,
                max_tokens=4000,
                response_format={"type": "json_object"},
            )
            return self._parse_article_json(response.choices[0].message.content)
        except Exception as e:
            logger.error(f"[OpenAI] Falha na geração: {e}")
            return None
```

- [ ] **Step 5: Implementar — extrair o construtor do prompt**

O corpo do `user_prompt` de `_generate_content` (a f-string que começa em `<dados_da_fonte>`) é reaproveitado integralmente, com duas mudanças: o `<output>` antigo sai e o `JSON_CONTRACT_BLOCK` entra.

Adicionar o método logo antes de `_generate_article_json`:

```python
    def _build_article_prompt(
        self,
        title: str,
        description: str,
        source: str,
        category: str,
        keyword: str,
        correction_hint: Optional[str] = None,
    ) -> str:
        """
        Monta o user prompt da chamada única.

        Reaproveita as seções que já existiam no prompt de conteúdo
        (<dados_da_fonte> até <validacao_obrigatoria>), troca o <output> antigo
        — que pedia "APENAS o artigo em Markdown", incompatível com JSON — pelo
        contrato de saída, e anexa o bloco de correção em retry.
        """
        cat_config = self._get_category_config(category)
        base = self._ARTICLE_PROMPT_TEMPLATE.format(
            title=title,
            description=description,
            category=category,
            tom=cat_config["tom"],
            foco=cat_config["foco"],
            keyword=keyword,
        )
        prompt = base + self.JSON_CONTRACT_BLOCK.format(keyword=keyword)

        if correction_hint:
            prompt += (
                "\n\n<correcao_obrigatoria>\n"
                "A geração anterior foi REPROVADA na validação editorial com estes problemas:\n"
                f"{correction_hint}\n\n"
                "Corrija TODOS esses problemas na nova geração. Se o problema foi "
                "word count abaixo do mínimo, EXPANDA as seções com mais contexto "
                "VERIFICÁVEL (regulação BR, dados on-chain, comparação histórica) — "
                "nunca com enchimento ou frases robóticas.\n"
                "</correcao_obrigatoria>"
            )
        return prompt
```

Mover o corpo da f-string de `_generate_content` para uma constante de classe `_ARTICLE_PROMPT_TEMPLATE`, declarada logo após `JSON_CONTRACT_BLOCK`:

```python
    # Corpo do prompt do artigo. Era a f-string de _generate_content; virou
    # template com campos nomeados para ser reaproveitado pela chamada única.
    # A seção <output> antiga foi REMOVIDA: ela pedia "APENAS o artigo em
    # Markdown", o que contradiz o contrato JSON.
    _ARTICLE_PROMPT_TEMPLATE = """<dados_da_fonte>
Título Original: {title}
Conteúdo da Fonte: {description}
Categoria: {category}
</dados_da_fonte>
...
（o restante do texto atual, sem alteração de conteúdo）
...
☐ ATRIBUIÇÃO: Dados específicos estão atribuídos à FONTE PRIMÁRIA (não a veículos nem a frases vagas)?
   → ✅ "Segundo relatório da [empresa]...", "De acordo com comunicado da SEC...", "Dados da Glassnode..."
   → ❌ "Segundo informações divulgadas...", "Conforme reportado...", "Fontes do setor..."
</validacao_obrigatoria>"""
```

**Três substituições exatas** no texto movido (verificado: o prompt tem 7 ocorrências de chave e todas são interpolações — não existe chave literal, então nada precisa ser duplicado como `{{`):

| De | Para | Onde |
|---|---|---|
| `{cat_config["tom"]}` | `{tom}` | seção `<configuracao_editorial>` |
| `{cat_config["foco"]}` | `{foco}` | seção `<configuracao_editorial>` |
| `{keyword_principal}` | `{keyword}` | **2 ocorrências**: `<configuracao_editorial>` e o item 2 de `<requisitos_tecnicos>` |

`{title}`, `{description}` e `{category}` ficam como estão.

**Corte:** o texto termina em `</validacao_obrigatoria>`. Tudo de `<output>` em diante sai — é o que o `JSON_CONTRACT_BLOCK` substitui.

- [ ] **Step 6: Rodar os testes novos**

Run: `python3 -m pytest tests/unit/test_content_generator_single_call.py -q`
Expected: PASS (7 testes)

- [ ] **Step 7: Reescrever os 2 testes de `correction_hint` que apontam para o método antigo**

Em `tests/unit/test_content_generator_sanitize.py`, remover `test_generate_content_injects_correction_hint_in_prompt` e `test_generate_content_omits_correction_block_when_no_hint`. A cobertura equivalente já existe em `test_content_generator_single_call.py` (`test_correction_hint_entra_no_prompt` e `test_sem_hint_nao_injeta_bloco_de_correcao`), agora apontando para o caminho que o produto de fato usa.

Run: `python3 -m pytest tests/unit/test_content_generator_sanitize.py -q`
Expected: PASS (3 testes restantes — os de `_sanitize_content` puro)

- [ ] **Step 8: Commit**

```bash
git add app/services/ai/content_generator.py tests/unit/test_content_generator_single_call.py tests/unit/test_content_generator_sanitize.py
git commit -m "feat(ai): _generate_article_json com contrato no prompt e fallback de provedor"
```

---

### Task 3: Religar `generate_article` e remover os métodos mortos

**Files:**
- Modify: `app/services/ai/content_generator.py` — `generate_article`; remover `_generate_content`, `_generate_seo_title`, `_generate_meta_description`
- Test: `tests/unit/test_content_generator_article.py` — reescrever os 3 testes

Este é o corte. `_generate_excerpt` **fica** — passa a ser fallback.

- [ ] **Step 1: Reescrever os testes**

Substituir o conteúdo inteiro de `tests/unit/test_content_generator_article.py`:

```python
"""
Testes do generate_article com a chamada única.

Os testes anteriores mockavam _generate_content, _generate_seo_title e
_generate_meta_description — três métodos que deixaram de existir. Agora
mockam o único ponto de contato com o LLM: _generate_article_json.
"""
import pytest

from app.services.ai.content_generator import ContentGenerator

CONTEUDO = "## Bitcoin em alta\n\n" + "Contexto do mercado de criptomoedas no Brasil. " * 40


def _json_do_llm(**overrides):
    dados = {
        "content_markdown": CONTEUDO,
        "title": "Bitcoin Sobe Forte Após Aprovação de ETF nos EUA",
        "excerpt": "Bitcoin renova máxima em meio a forte demanda institucional por ETFs listados na bolsa americana.",
        "meta_description": "Entenda o que a alta do Bitcoin significa para o investidor brasileiro e o que observar nos próximos meses.",
    }
    dados.update(overrides)
    return dados


def _news(**extra):
    news = {
        "title": "Bitcoin Hits New All-Time High",
        "description": "resumo curto do RSS",
        "source": "CoinDesk",
        "url": "https://coindesk.com/noticia",
    }
    news.update(extra)
    return news


def _gen_com_json(monkeypatch, payload, capturado=None):
    gen = ContentGenerator()

    async def fake(title, description, source, category="default", correction_hint=None):
        if capturado is not None:
            capturado["description"] = description
            capturado["correction_hint"] = correction_hint
        return payload

    monkeypatch.setattr(gen, "_generate_article_json", fake)
    return gen


@pytest.mark.asyncio
async def test_monta_o_artigo_a_partir_do_json(monkeypatch):
    gen = _gen_com_json(monkeypatch, _json_do_llm())

    article = await gen.generate_article(_news())

    assert article["title"] == "Bitcoin Sobe Forte Após Aprovação de ETF nos EUA"
    assert article["meta_title"] == article["title"]
    assert article["slug"] == "bitcoin-sobe-forte-apos-aprovacao-de-etf-nos-eua"
    assert article["source_url"] == "https://coindesk.com/noticia"
    assert article["source_name"] == "CoinDesk"


@pytest.mark.asyncio
async def test_prefere_full_text_sobre_description(monkeypatch):
    """O texto completo da matéria original é melhor material que o resumo RSS."""
    capturado = {}
    gen = _gen_com_json(monkeypatch, _json_do_llm(), capturado)

    await gen.generate_article(_news(full_text="texto completo extraído da matéria"))

    assert capturado["description"] == "texto completo extraído da matéria"


@pytest.mark.asyncio
async def test_sem_full_text_usa_description(monkeypatch):
    capturado = {}
    gen = _gen_com_json(monkeypatch, _json_do_llm(), capturado)

    await gen.generate_article(_news())

    assert capturado["description"] == "resumo curto do RSS"


@pytest.mark.asyncio
async def test_json_nulo_descarta_o_artigo(monkeypatch):
    """Sem JSON aproveitável não há artigo — o pipeline tenta a próxima notícia."""
    gen = _gen_com_json(monkeypatch, None)

    assert await gen.generate_article(_news()) is None


@pytest.mark.asyncio
async def test_conteudo_passa_pela_sanitizacao(monkeypatch):
    """
    _sanitize_content rodava dentro de _generate_content. Ao mover a geração
    para o JSON, era fácil perder essa etapa — este teste é a guarda.
    """
    gen = _gen_com_json(
        monkeypatch,
        _json_do_llm(content_markdown="## Manchete\n\nSegundo o CoinDesk, o preço subiu."),
    )

    article = await gen.generate_article(_news())

    assert "CoinDesk" not in article["content_markdown"]


@pytest.mark.asyncio
async def test_excerpt_do_llm_e_usado_quando_esta_na_faixa(monkeypatch):
    gen = _gen_com_json(monkeypatch, _json_do_llm())

    article = await gen.generate_article(_news())

    assert article["excerpt"].startswith("Bitcoin renova máxima")


@pytest.mark.asyncio
@pytest.mark.parametrize("excerpt_ruim", [None, "curto demais", "x" * 250])
async def test_excerpt_fora_da_faixa_cai_no_fallback_mecanico(monkeypatch, excerpt_ruim):
    """
    O validador exige 80 a 200 chars. Excerpt fora disso é derivado do
    conteúdo em vez de descartar o artigo inteiro — mesmo princípio que
    motiva a consolidação.
    """
    gen = _gen_com_json(monkeypatch, _json_do_llm(excerpt=excerpt_ruim))

    article = await gen.generate_article(_news())

    assert article is not None
    assert article["excerpt"] != excerpt_ruim
    assert article["excerpt"].startswith("Contexto do mercado")


@pytest.mark.asyncio
async def test_correction_hint_e_repassado(monkeypatch):
    capturado = {}
    gen = _gen_com_json(monkeypatch, _json_do_llm(), capturado)

    await gen.generate_article(_news(), correction_hint="word count baixo")

    assert capturado["correction_hint"] == "word count baixo"
```

- [ ] **Step 2: Rodar para confirmar que falham**

Run: `python3 -m pytest tests/unit/test_content_generator_article.py -q`
Expected: FAIL — `generate_article` ainda chama `_generate_content` (não mockado, tenta rede/cliente real) e não conhece o caminho do JSON. Alguns testes podem também acusar `AttributeError` no `monkeypatch.setattr` se o método ainda não existir; ele existe desde a Task 2, então o modo dominante é falha de asserção e erro de cliente.

- [ ] **Step 3: Implementar — religar `generate_article`**

Substituir o corpo do `try` de `generate_article` (das linhas que hoje vão de `title = source_news.get("title", "")` até a montagem do dict `article`) por:

```python
            title = source_news.get("title", "")
            # Preferir o texto completo extraído da matéria original
            # (ArticleExtractor); o resumo do RSS é o fallback — com 1-2
            # frases o LLM não tem material para 700+ palavras sem alucinar.
            description = source_news.get("full_text") or source_news.get("description", "")
            source = source_news.get("source", "")

            logger.info(f"Gerando artigo para: {title[:50]}... (categoria: {category})")

            dados = await self._generate_article_json(
                title, description, source, category, correction_hint
            )
            if not dados:
                logger.warning("Falha ao gerar artigo (JSON inaproveitável)")
                return None

            # A sanitização rodava dentro de _generate_content; agora incide
            # sobre o content_markdown que veio do JSON.
            content = self._sanitize_content(dados["content_markdown"])
            seo_title = dados["title"].strip()

            # Excerpt: o do LLM se estiver na faixa que o validador aceita
            # (80-200), senão derivado do conteúdo. Fora de faixa não pode
            # custar o descarte de um artigo já gerado.
            excerpt = (dados.get("excerpt") or "").strip()
            if not (self.MIN_EXCERPT_LENGTH <= len(excerpt) <= self.MAX_EXCERPT_LENGTH):
                if excerpt:
                    logger.warning(
                        f"Excerpt do LLM fora da faixa ({len(excerpt)} chars) — "
                        f"derivando do conteúdo"
                    )
                excerpt = await self._generate_excerpt(content)

            article = {
                "title": seo_title,
                "slug": slugify(seo_title),
                "content_markdown": content,
                "excerpt": excerpt,
                "meta_title": seo_title,
                "meta_description": (dados.get("meta_description") or "").strip() or None,
                "source_url": source_news.get("url"),
                "source_name": source,
                "category": category,
            }
```

Adicionar as constantes de faixa na classe, logo após `REQUIRED_ARTICLE_FIELDS` (espelham `QualityValidator.MIN/MAX_EXCERPT_LENGTH`, e existem aqui para decidir o fallback **antes** de chegar ao validador):

```python
    # Faixa de excerpt que o QualityValidator aceita. Duplicada aqui de
    # propósito: precisamos decidir o fallback antes da validação, não depois
    # de o artigo ser reprovado.
    MIN_EXCERPT_LENGTH = 80
    MAX_EXCERPT_LENGTH = 200
```

- [ ] **Step 4: Implementar — remover os métodos mortos**

Remover integralmente de `app/services/ai/content_generator.py`:
- `_generate_content` (o método inteiro; o corpo da f-string já virou `_ARTICLE_PROMPT_TEMPLATE` na Task 2)
- `_generate_seo_title`
- `_generate_meta_description`

Manter `_generate_excerpt` — é o fallback.

- [ ] **Step 5: Rodar os testes**

Run: `python3 -m pytest tests/unit/test_content_generator_article.py tests/unit/test_content_generator_excerpt.py -q`
Expected: PASS (12 testes — 10 de artigo (7 simples + 1 parametrizado de 3 casos) mais os 2 de excerpt, que sobrevivem porque o método continua existindo)

- [ ] **Step 6: Confirmar que os métodos mortos sumiram**

```bash
grep -n "_generate_seo_title\|_generate_meta_description" app/ -r || echo "metodos removidos ✓"
grep -n "async def _generate_content" app/services/ai/content_generator.py || echo "_generate_content removido do ContentGenerator ✓"
```
Expected: as duas confirmações. Atenção: `weekly_report_generator.py` tem um `_generate_content` **próprio** (classe diferente) que deve continuar existindo — o segundo grep é restrito ao arquivo certo por isso.

- [ ] **Step 7: Commit**

```bash
git add app/services/ai/content_generator.py tests/unit/test_content_generator_article.py
git commit -m "refactor(ai): generate_article usa a chamada unica; remove os 3 metodos antigos"
```

---

### Task 4: Corrigir a contagem no comentário do pipeline

**Files:**
- Modify: `app/services/automation/news_pipeline.py` — comentário do pré-filtro

O comentário afirma "4 chamadas de LLM". São 3 (conteúdo, título, meta) — e depois desta consolidação, 1. Imprecisão registrada em código na primeira rodada.

- [ ] **Step 1: Corrigir**

Substituir, no comentário do bloco de pré-filtro:

```python
            # Pré-filtro: descarta notícias cuja URL já virou post nos
            # últimos 7 dias. A coleta olha 24h para trás e o cron roda
            # várias vezes ao dia — sem isso, a mesma notícia era regerada
            # (1 chamada de LLM por artigo) em cada run só para o dedup
            # descartá-la.
```

- [ ] **Step 2: Confirmar**

```bash
grep -n "4 chamadas de LLM" app/ -r || echo "contagem corrigida ✓"
```
Expected: `contagem corrigida ✓`

- [ ] **Step 3: Commit**

```bash
git add app/services/automation/news_pipeline.py
git commit -m "docs: corrige contagem de chamadas de LLM no comentario do pre-filtro"
```

---

### Task 5: Verificação final

**Files:** nenhum (verificação)

- [ ] **Step 1: Suíte completa**

Run: `python3 -m pytest tests/ -q 2>&1 | tail -3`
Expected: `376 passed, 0 failed, 0 errors`.

A conta: baseline 353, menos os 5 testes substituídos (3 de `test_content_generator_article.py` e 2 de `test_content_generator_sanitize.py`) = 348; mais 11 de parse, 7 de chamada única e 10 novos de artigo = **376**.

Se o total divergir, o que importa verificar é: zero failed, zero errors, e nenhum teste pré-existente perdido além dos 5 substituídos.

- [ ] **Step 2: Contagem de chamadas de LLM no fluxo real**

```bash
T=$(python3 -c "import secrets;print(secrets.token_urlsafe(32))"); \
SECRET_KEY=$T AUTOMATION_TOKEN=$T REVALIDATE_SECRET=$T \
DATABASE_URL="sqlite+aiosqlite:///:memory:" python3 -c "
import asyncio, json
from unittest.mock import AsyncMock, MagicMock
from app.services.ai.content_generator import ContentGenerator

gen = ContentGenerator()
chamadas = []
async def gc(**kw):
    chamadas.append(kw)
    r = MagicMock()
    r.text = json.dumps({
        'content_markdown': '## M\n\n' + 'palavra ' * 800,
        'title': 'Bitcoin Atinge Máxima Histórica Após Aprovação de ETF',
        'excerpt': 'Bitcoin renova máxima em meio a forte demanda institucional por ETFs listados.',
        'meta_description': 'Entenda o que a máxima do Bitcoin significa para o investidor brasileiro hoje e adiante.',
    })
    return r
gen.gemini_client = MagicMock()
gen.gemini_client.aio.models.generate_content = AsyncMock(side_effect=gc)
gen.use_gemini = True

art = asyncio.run(gen.generate_article({'title':'t','description':'d','source':'CoinDesk','url':'u'}))
print('  chamadas de LLM:', len(chamadas), '(antes: 3)')
print('  artigo montado:', art is not None)
print('  excerpt:', len(art['excerpt']), 'chars (faixa 80-200)')
print('  meta:', len(art['meta_description'] or ''), 'chars')
" 2>&1 | grep "^  "
```
Expected: `chamadas de LLM: 1`, artigo montado `True`, excerpt dentro de 80–200.

- [ ] **Step 3: Confirmar que o log de falha de parse é `error`**

O spec exige nível `error` na falha de parse, para que uma degradação do modelo apareça no monitoramento em vez de virar queda inexplicada de volume.

```bash
grep -n "logger.error" app/services/ai/content_generator.py | grep -i "json"
```
Expected: pelo menos as linhas de `[JSON] Parse falhou mesmo com json_repair`, `[JSON] Esperado objeto` e `[JSON] Campo obrigatório ausente ou vazio`.

- [ ] **Step 4: Nota de deploy**

Nenhuma migration, nenhuma env var. `json_repair` já está no `requirements.txt` (usado pelo `AirdropPostGenerator`). O deploy é só o código.

**O que observar depois do deploy:** a taxa de `[JSON]` em nível `error`. Se subir, o modelo está devolvendo JSON que o `json_repair` não conserta, e o caminho a considerar é adotar `response_schema` nativo no Gemini (deliberadamente fora deste escopo).

---

## Fora do escopo deste plano (deliberadamente adiado)

- **`response_schema` nativo do Gemini.** Descartado com razão registrada no spec: o fallback OpenAI precisa do mesmo contrato, e enforcement nativo exigiria duas implementações. É o próximo passo se o parse se mostrar frágil em produção.
- **Artigos-panorama poluindo o pipeline.** Digests do tipo "Here's what happened in crypto today" são ímãs de falso positivo no dedup e provavelmente não deveriam virar post. Item próprio.
- **Novas fontes** (SEC, fontes brasileiras, ligar o `MarketDataCollector` ao pipeline de notícias). Sub-projeto seguinte.
- **Fallback para `meta_description` ausente.** Sem fallback de boa qualidade (truncar o excerpt daria meta ruim para SEO), a ausência custa um retry. Resíduo aceito no spec.

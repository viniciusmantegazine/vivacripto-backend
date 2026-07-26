# Fronteira de palavra na remoção de nomes de veículos — Plano de Implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Parar a corrupção de artigos publicados (`the blockchain` → `chain`, `decrypted` → `ed`) e o alerta `[Sanitização CRÍTICA]` falso, trocando as checagens de substring de `_sanitize_content` por casamento com fronteira de palavra.

**Architecture:** As duas listas de configuração (nomes de veículos e a exceção case-sensitive) sobem para atributos de classe, o que as torna testáveis. O gatilho e a remoção final passam de substring (`in` / `str.replace`) para `re.search` / `re.sub` com `\b...\b`. Os dois regexes de frase atributiva já tinham fronteira e mudam apenas para receber o flag de caixa por nome, em vez do `(?i)` embutido — assim as três operações sobre um mesmo nome usam a mesma sensibilidade.

**Tech Stack:** Python 3.11+, `re`, pytest (testes síncronos e puros — `_sanitize_content` não faz I/O nem chama LLM).

---

## Contexto essencial para o executor

- **Rodar testes:** `python3 -m pytest tests/unit/... -q` (não existe venv; use `python3`).
- **Baseline (2026-07-26):** `335 passed, 0 failed, 0 errors`. Nenhum teste deve regredir.
- **Comentários de código em português** (convenção do projeto).
- **O bug em uma frase:** a lista de veículos contém variantes em minúscula (`"decrypt"`, `"the block"`) e o casamento é por substring, então `"decrypted"` e `"the blockchain"` são tratados como nome de veículo.
- **Por que o gatilho importa tanto quanto a remoção:** `if site_name in result` é a mesma checagem de substring. Além de habilitar a corrupção, ela emite `[Sanitização CRÍTICA] LLM violou regra e citou veículo 'decrypt'` quando o LLM não violou nada — ruído que torna o alerta inútil para quem monitora.
- **Por que `The Block` é exceção:** `\bthe block\b` casa com a frase inglesa (`the block height`, `the block reward`) exatamente como casa com o nome do veículo. Fronteira de palavra sozinha não distingue os dois; a caixa distingue. Este é o único nome da lista cuja forma minúscula é vocabulário cripto de alta frequência.
- **Remover o `(?i)` embutido é obrigatório, não cosmético.** Um `(?i)` dentro do padrão força case-insensitive e **ignora** `flags=0`, então a exceção de `The Block` não funcionaria nos regexes de frase atributiva se o `(?i)` ficasse.
- **Teste existente que precisa continuar passando:** `tests/unit/test_content_generator_sanitize.py::test_sanitize_removes_site_mention_and_keeps_breaks` usa `"Segundo o CoinDesk, ..."`. `CoinDesk` segue case-insensitive, então ele passa sem alteração. Se quebrar, a mudança foi além do pretendido.

---

### Task 1: Fronteira de palavra no gatilho, nos regexes e na remoção final

**Files:**
- Modify: `app/services/ai/content_generator.py` — atributos de classe novos; substituir o bloco das linhas 563-576 (lista local) e 643-667 (loop de remoção)
- Test: `tests/unit/test_content_generator_sanitize_boundary.py` (novo)

- [ ] **Step 1: Escrever os testes que falham**

Criar `tests/unit/test_content_generator_sanitize_boundary.py`:

```python
"""
Testes de fronteira de palavra na remoção de nomes de veículos.

Bug corrigido aqui: a lista de veículos tinha variantes em minúscula
("decrypt", "the block") e o casamento era por substring, então
vocabulário técnico normal era tratado como nome de veículo. Medido no
código anterior:

    "A transação foi decrypted pelo protocolo."  -> "A transação foi ed ..."
    "Dados via the blockchain publica."          -> "Dados via chain publica."

O mesmo defeito emitia "[Sanitização CRÍTICA] LLM violou regra e citou
veículo 'decrypt'" quando o LLM não havia citado nada.
"""
import pytest

from app.services.ai.content_generator import ContentGenerator


@pytest.fixture
def generator() -> ContentGenerator:
    return ContentGenerator()


# --- Grupo 1: vocabulário técnico deve sair intacto -------------------------

@pytest.mark.parametrize(
    "texto",
    [
        "A transação foi decrypted pelo protocolo de rede.",
        "O processo de decryption garante privacidade ao usuário.",
        "Dados armazenados on-chain via the blockchain publica.",
        "Analistas avaliam the block height atual da rede Bitcoin.",
    ],
)
def test_vocabulario_tecnico_nao_e_corrompido(generator: ContentGenerator, texto: str):
    """
    Regressão: substring fazia "decrypt" casar dentro de "decrypted" e
    "the block" dentro de "the blockchain".

    O caso "the block height" só passa por causa da exceção case-sensitive
    de `The Block` — fronteira de palavra sozinha não resolve esse.
    """
    assert generator._sanitize_content(texto) == texto


# --- Grupo 2: citação real de veículo deve ser removida --------------------

@pytest.mark.parametrize(
    "texto,proibido",
    [
        ("Segundo o CoinDesk, o Bitcoin subiu forte.", "CoinDesk"),
        ("The Block informou que houve um incidente.", "The Block"),
        ("Conforme o Decrypt, a rede ficou instável.", "Decrypt"),
        ("segundo o cointelegraph, houve queda no volume.", "cointelegraph"),
    ],
)
def test_citacao_de_veiculo_continua_removida(
    generator: ContentGenerator, texto: str, proibido: str
):
    """A correção não pode afrouxar o propósito original da sanitização."""
    resultado = generator._sanitize_content(texto)

    assert proibido.lower() not in resultado.lower()


# --- Grupo 3: provedores de dados são permitidos --------------------------

@pytest.mark.parametrize(
    "provedor",
    ["CoinGecko", "Glassnode", "Chainalysis"],
)
def test_provedores_de_dados_nao_sao_removidos(
    generator: ContentGenerator, provedor: str
):
    """
    O prompt permite explicitamente provedores de DADOS (não são veículos
    jornalísticos). Guarda contra alguém adicioná-los à lista por engano.
    """
    texto = f"Dados da {provedor} mostram alta no volume negociado."

    assert provedor in generator._sanitize_content(texto)


# --- Grupo 4: invariantes da configuração --------------------------------

def test_lista_de_veiculos_nao_tem_duplicata_de_caixa():
    """
    As variantes de caixa existiam só porque a remoção era case-sensitive.
    Com regex + re.IGNORECASE elas são redundantes, e reintroduzi-las
    ressuscitaria a confusão que causou o bug.
    """
    nomes = list(ContentGenerator.SOURCE_SITE_NAMES)
    minusculos = [n.lower() for n in nomes]

    assert len(minusculos) == len(set(minusculos)), (
        f"duplicata de caixa na lista: {nomes}"
    )


def test_excecao_case_sensitive_esta_documentada():
    """
    `The Block` casa case-sensitive porque "the block" é vocabulário cripto
    comum. Este teste impede que a exceção seja removida por engano num
    refactor futuro, ou estendida sem intenção.
    """
    assert "The Block" in ContentGenerator.CASE_SENSITIVE_SITE_NAMES
    assert "CoinDesk" not in ContentGenerator.CASE_SENSITIVE_SITE_NAMES
    # Todo nome da exceção precisa existir na lista principal
    assert ContentGenerator.CASE_SENSITIVE_SITE_NAMES.issubset(
        set(ContentGenerator.SOURCE_SITE_NAMES)
    )
```

- [ ] **Step 2: Rodar para confirmar que falham**

Run: `python3 -m pytest tests/unit/test_content_generator_sanitize_boundary.py -q`
Expected: FAIL em 6 dos 13 testes.
- Os 4 de `test_vocabulario_tecnico_nao_e_corrompido` falham por corrupção do texto (`AssertionError` comparando a string).
- `test_lista_de_veiculos_nao_tem_duplicata_de_caixa` e `test_excecao_case_sensitive_esta_documentada` falham com `AttributeError: type object 'ContentGenerator' has no attribute 'SOURCE_SITE_NAMES'` / `CASE_SENSITIVE_SITE_NAMES` — os atributos ainda não existem.
- Os 4 de citação e os 3 de provedor de dados já passam (o comportamento atual já os atende); eles existem como guarda de não-regressão.

- [ ] **Step 3: Implementar — atributos de classe**

Em `app/services/ai/content_generator.py`, adicionar os dois atributos na classe `ContentGenerator`, imediatamente após a constante `OPENAI_MODEL` (que está logo abaixo de `GEMINI_MODEL`, perto do topo da classe):

```python
    # Veículos jornalísticos concorrentes que NUNCA devem aparecer no texto
    # gerado. SEM variantes de caixa: o casamento é por regex com
    # re.IGNORECASE. Reintroduzir "coindesk" ao lado de "CoinDesk" é o que
    # causou a corrupção de texto corrigida aqui.
    SOURCE_SITE_NAMES = (
        "CoinDesk",
        "CoinTelegraph",
        "CryptoSlate",
        "Bitcoin Magazine",
        "Decrypt",
        "The Block",
        "CoinPaper",
        "CoinRepo",
        "BeInCrypto",
        "NewsBTC",
        "CryptoNews",
    )

    # Exceção: "the block" (artigo + substantivo) é vocabulário central de
    # cripto — "the block height", "the block reward", "the block size".
    # Casar este nome case-SENSITIVE preserva essas frases e ainda pega
    # "The Block informou que...", porque LLM capitaliza nome próprio.
    # Custo aceito: menção ao veículo escrita toda em minúscula escapa.
    CASE_SENSITIVE_SITE_NAMES = frozenset({"The Block"})
```

- [ ] **Step 4: Implementar — remover a lista local**

Substituir as linhas 563-576 (a lista local `source_site_names`, do comentário `# Nomes de sites/fontes...` até o `]` que a fecha) por:

```python
        # A lista de veículos agora é o atributo de classe SOURCE_SITE_NAMES.
```

- [ ] **Step 5: Implementar — o loop de remoção**

Substituir o bloco das linhas 643-667 (do comentário `# Remover menções a veículos...` até o `result = result.replace(site_name, "")` inclusive) por:

```python
        # Remover menções a veículos jornalísticos concorrentes (v4.0)
        # ATENÇÃO: NÃO injetar frases-tique como "informações divulgadas"/"fontes do setor"
        # — esse é o fingerprint de IA que o Google penaliza. Se o LLM violou o prompt,
        # remover a frase introdutória inteira e logar ERROR para investigação.
        #
        # Todo casamento usa \b...\b. Com substring, "decrypted" casava em
        # "decrypt" e "the blockchain" em "the block" — corrompendo o texto
        # ("the blockchain" virava "chain") e emitindo alerta CRÍTICO falso.
        # NÃO usar (?i) embutido: ele ignora `flags` e quebraria a exceção
        # case-sensitive de The Block.
        for site_name in self.SOURCE_SITE_NAMES:
            flags = (
                0 if site_name in self.CASE_SENSITIVE_SITE_NAMES else re.IGNORECASE
            )
            padrao_nome = rf'\b{re.escape(site_name)}\b'

            if not re.search(padrao_nome, result, flags):
                continue

            logger.error(
                f"[Sanitização CRÍTICA] LLM violou regra e citou veículo '{site_name}'. "
                f"Removendo frase atributiva. Revisar prompt se reincidir."
            )
            # Remover frase introdutória completa: "Segundo o CoinDesk, ..."
            result = re.sub(
                rf'\b(segundo|de acordo com|conforme|para|por)\s+(o|a|o portal|o site)?\s*{re.escape(site_name)}\b\s*[,.]?\s*',
                '',
                result,
                flags=flags,
            )
            # Remover construções "o CoinDesk informou/reportou/publicou X" -> "X"
            result = re.sub(
                rf'\b(o|a|o portal|o site)?\s*{re.escape(site_name)}\s+(informou|reportou|publicou|divulgou|noticiou|revelou)\s+que\s+',
                '',
                result,
                flags=flags,
            )
            # Remoção final: qualquer ocorrência restante do nome. Sem guarda
            # de `if`: re.sub não faz nada quando não há casamento.
            result = re.sub(padrao_nome, '', result, flags=flags)
```

- [ ] **Step 6: Rodar os testes novos**

Run: `python3 -m pytest tests/unit/test_content_generator_sanitize_boundary.py -q`
Expected: PASS (13 testes)

- [ ] **Step 7: Rodar os testes de sanitize existentes**

Run: `python3 -m pytest tests/unit/test_content_generator_sanitize.py -q`
Expected: PASS (5 testes, sem alteração no arquivo). `test_sanitize_removes_site_mention_and_keeps_breaks` é o que importa aqui — ele usa `"Segundo o CoinDesk"` e prova que a remoção legítima continua funcionando e preservando `\n\n`.

- [ ] **Step 8: Commit**

```bash
git add app/services/ai/content_generator.py tests/unit/test_content_generator_sanitize_boundary.py
git commit -m "fix(ai): fronteira de palavra na remocao de veiculos (the blockchain virava chain)"
```

---

### Task 2: Verificação final

**Files:** nenhum (verificação)

- [ ] **Step 1: Suíte completa sem regressão**

Run: `python3 -m pytest tests/ -q 2>&1 | tail -3`
Expected: `348 passed, 0 failed, 0 errors` — baseline de 335 mais os 13 testes novos.

- [ ] **Step 2: Confirmar que não sobrou casamento por substring**

```bash
grep -n "site_name in result\|result.replace(site_name" app/services/ai/content_generator.py || echo "sem substring ✓"
grep -n '(?i)' app/services/ai/content_generator.py || echo "sem (?i) embutido ✓"
grep -cn "coindesk\|cointelegraph\|cryptoslate\|beincrypto\|newsbtc\|cryptonews" app/services/ai/content_generator.py
```
Expected: as duas linhas de confirmação. A última contagem deve refletir só ocorrências nos prompts (que citam os nomes como proibidos ao LLM), não variantes na lista de configuração.

- [ ] **Step 3: Reproduzir os 4 casos de corrupção no código corrigido**

```bash
T=$(python3 -c "import secrets;print(secrets.token_urlsafe(32))"); \
SECRET_KEY=$T AUTOMATION_TOKEN=$T REVALIDATE_SECRET=$T \
DATABASE_URL="sqlite+aiosqlite:///:memory:" python3 -c "
from app.services.ai.content_generator import ContentGenerator
g = ContentGenerator()
casos = [
    'A transação foi decrypted pelo protocolo de rede.',
    'O processo de decryption garante privacidade ao usuário.',
    'Dados armazenados on-chain via the blockchain publica.',
    'Analistas avaliam the block height atual da rede Bitcoin.',
]
for c in casos:
    out = g._sanitize_content(c)
    print(('  INTACTO   ' if out == c else '  QUEBROU  ') + '| ' + c)
print('  lista:', len(ContentGenerator.SOURCE_SITE_NAMES), 'nomes | excecao:', set(ContentGenerator.CASE_SENSITIVE_SITE_NAMES))
" 2>&1 | grep "^  "
```
Expected: `INTACTO` nos 4, `lista: 11 nomes | excecao: {'The Block'}`.

- [ ] **Step 4: Confirmar que citação real continua sendo removida**

```bash
T=$(python3 -c "import secrets;print(secrets.token_urlsafe(32))"); \
SECRET_KEY=$T AUTOMATION_TOKEN=$T REVALIDATE_SECRET=$T \
DATABASE_URL="sqlite+aiosqlite:///:memory:" python3 -c "
from app.services.ai.content_generator import ContentGenerator
g = ContentGenerator()
for c in ['Segundo o CoinDesk, o Bitcoin subiu.',
          'The Block informou que houve incidente.',
          'Conforme o Decrypt, a rede parou.',
          'segundo o cointelegraph, houve queda.']:
    print('  ' + repr(g._sanitize_content(c)))
" 2>&1 | grep "^  "
```
Expected: as 4 saídas sem o nome do veículo. O log de `[Sanitização CRÍTICA]` aparece nas 4 — aqui ele é correto, porque houve citação de fato.

- [ ] **Step 5: Nota de deploy**

Nenhuma migration, nenhuma env var, nenhuma dependência nova. O deploy é só o código.

---

## Fora do escopo deste plano (deliberadamente adiado)

- **Consolidar as 3 chamadas de LLM em 1.** Próximo sub-projeto, com spec próprio. Toca `generate_article` e os métodos `_generate_*`; este bug vive em `_sanitize_content`.
- **`temperature` nas chamadas de título/meta.** Dissolve-se na consolidação — aquelas chamadas deixam de existir.
- **Corrigir o comentário do `news_pipeline.py` que diz "4 chamadas de LLM".** São 3. Vai junto no spec da consolidação, onde o número é o assunto.
- **Artefatos de pontuação órfã.** Remover `"CoinDesk"` de `"o CoinDesk's relatório"` deixa `"'s"`. A limpeza existente já trata espaço duplo e vírgula órfã; possessivo em inglês é raro em texto PT.
- **Mover as outras listas locais (`forbidden_prefixes`, `nfa_red_flags`, `robotic_phrases`) para atributos de classe.** Só as duas de veículo subiram, porque só elas precisam ser acessíveis a teste. Uniformizar o resto é refactor sem demanda.

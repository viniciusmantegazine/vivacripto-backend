# Gotchas e Conhecimento Tácito

Este documento captura o conhecimento que desenvolvedores experientes acumulam ao longo do tempo - as "armadilhas" não documentadas, comportamentos contra-intuitivos e workarounds que são essenciais para trabalhar efetivamente neste repositório.

## Armadilhas Comuns

### 1. Configuração de Ambiente - Ordem de Chaves de API

**Sintoma**: Pipeline de automação falha silenciosamente ou usa fallback quando não deveria.

**Causa**: As chaves de API precisam ser configuradas na ordem correta de prioridade.

**Solução**: Configure na seguinte ordem de prioridade:
1. `GEMINI_API_KEY` - Primário (mais econômico)
2. `OPENAI_API_KEY` - Fallback (mais caro)
3. `CLOUDINARY_*` - Para upload de imagens

**Contexto**: O sistema usa Gemini como primário e OpenAI como fallback. Se Gemini falhar silenciosamente (chave inválida), todo o custo vai para OpenAI.

**Verificação**:
```bash
# Teste a chave Gemini antes de usar em produção
curl -X POST "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=$GEMINI_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"contents":[{"parts":[{"text":"Hello"}]}]}'
```

---

### 2. AI Fallbacks - Comportamento Silencioso

**Sintoma**: Custos de API maiores que esperado; logs mostram muitos fallbacks.

**Causa**: Quando Gemini falha, o sistema automaticamente usa OpenAI sem interromper a execução.

**Solução**:
- Monitore logs para warnings de fallback
- Verifique regularmente os custos de cada API
- Configure alertas para taxa alta de fallbacks

**Arquivos relacionados**:
- `app/services/ai/content_generator.py` (linhas 340-370)
- `app/services/ai/image_generator.py` (linhas 170-206)

**Padrão de log para monitorar**:
```
[ContentGen] Gemini failed, trying OpenAI...
[ImageGen] Gemini image generation failed, falling back to DALL-E
```

---

### 3. Threshold de Deduplicação ✅ RECALIBRADO (2026-08-15)

**Sintoma (histórico)**: Duplicatas eram publicadas no site — em agosto/2026
dois pares chegaram ao ar (Tether/KPMG em 13-14/08 e Luke Dashjr duas vezes em
11/08), ambos dentro da janela de 24h que o detector compara.

**Causa**: O threshold de 0.80 foi calibrado para o engine de embeddings
(sentence-transformers), que foi removido dos requirements. O engine de
produção é o TF-IDF (`DEDUPLICATION_ENGINE = "tfidf"`, default), onde
duplicata real pontua 0.72–0.73 — o 0.80 nunca disparava e a camada estava
morta. A tabela antiga desta seção (produção = 0.80/embedding) descrevia uma
configuração que não existia mais.

**Solução aplicada**: `DEDUPLICATION_THRESHOLD = 0.55`, calibrado sobre
artigos publicados reais comparados como o detector compara (título + resumo +
conteúdo[:500]): duplicata verdadeira 0.72–0.73; mesma pauta com ângulo
próprio 0.40; distintas ≤ 0.27. A fronteira editorial está travada em
`tests/unit/test_duplicate_detector.py` com os textos reais dos pares.

**Ao recalibrar**: erre para cima. Falso positivo dispara `UPDATE_EXISTING`,
que SOBRESCREVE o post existente — pior que publicar duplicata. E lembre que
threshold e engine calibram JUNTOS: trocar o engine invalida o valor
(o teste `_detector_de_producao` trava essa dependência).

**Atenção deploy**: se a Railway definir `DEDUPLICATION_THRESHOLD` ou
`DEDUPLICATION_ENGINE` como variável de ambiente, o env sobrepõe o default do
código — confira que não há override com os valores antigos.

**Diagnóstico**:
```python
# No log, procure por:
# "Similaridade com '...': 0.XX"  (debug) e "Similaridade máxima: ..." (info)
```

---

### 4. Redis Opcional - Impacto em Performance

**Sintoma**: Deduplicação muito lenta em produção; mesmos embeddings recalculados repetidamente.

**Causa**: Sem Redis, o cache de embeddings é em memória e perdido entre requests.

**Solução**:
- **Desenvolvimento**: Redis opcional (funciona sem)
- **Produção**: Redis **fortemente recomendado**

**Impacto sem Redis**:
- Cada deduplicação recalcula embeddings (~500ms por post)
- Sem cache de sessão entre execuções
- Rate limiting usa memória (perdido em restart)

**Configuração**:
```bash
# Produção - adicione Redis
REDIS_URL=redis://default:xxx@redis.railway.internal:6379
```

---

### 5. Tokens Inseguros em Produção

**Sintoma**: Aplicação não inicia em produção com erro de validação.

**Causa**: Tokens com valores default ou muito curtos são bloqueados em `DEBUG=false`.

**Solução**: Todos os tokens devem ter mínimo 32 caracteres e não podem ser valores default.

**Valores bloqueados**:
```python
INSECURE_DEFAULTS = [
    "your-secret-key-change-in-production",
    "automation-service-token-change-in-production",
    "revalidation-secret-change-in-production",
    "secret",
    "changeme",
    "password",
    "",
]
```

**Geração de tokens seguros**:
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

---

### 6. Testes — UUID PostgreSQL vs SQLite ✅ RESOLVIDO (2026-07-26)

**Sintoma (histórico)**: Qualquer teste que usasse a fixture `db_session` quebrava com:
```
sqlalchemy.exc.CompileError: Compiler can't render element of type UUID
```

**Causa**: `app/db/models.py` importava `UUID`/`JSONB` de `sqlalchemy.dialects.postgresql` (tipos Postgres-only). Os testes rodam SQLite in-memory, que não compila esses tipos. 47 testes morriam antes de executar uma linha.

**Solução aplicada**: `app/db/types.py` define os TypeDecorators portáteis:
- `GUID` — `UUID` nativo no Postgres, `CHAR(36)` no resto. Sempre devolve `uuid.UUID`, aceita `uuid.UUID` ou `str` na entrada.
- `PortableJSONB` — `JSONB` no Postgres, `JSON` no resto.

`models.py` usa esses tipos. **As migrations Alembic seguem declarando `postgresql.UUID`/`JSONB` direto** — rodam só contra Postgres, não precisam (nem devem) ser portáteis.

**Ao escrever testes novos**: `db_session` funciona normalmente, use-a. O padrão de mockar `AsyncSession` (ainda presente em `tests/integration/test_api_airdrops_*.py` e em vários testes deste repo) continua válido para testes de unidade que não querem tocar banco, mas não é mais uma obrigação imposta por este gotcha.

**Lição**: enquanto os 47 testes ficaram cegos, dois bugs se esconderam atrás deles — `httpx 0.28` quebrando a fixture `api_client` (removeu `AsyncClient(app=...)`, exige `ASGITransport`) e 9 chamadas `PostCreate` sem o campo obrigatório `excerpt`. Teste que não roda não é rede de segurança; é passivo.

---

### 7. Testes — Rate Limiter Compartilhado

**Sintoma**: Tests de integração começam a retornar 429 quando rodados em sequência, mesmo isoladamente bem.

**Causa**: `slowapi.Limiter` é singleton por processo. O contador é compartilhado entre tests do mesmo endpoint.

**Solução**: `tests/conftest.py` faz monkey-patch de `slowapi.Limiter.limit` pra um no-op decorator. Isso desativa rate limiting em **todos** os testes.

**Implicação**: Não dá pra testar lógica de rate limit via pytest sem reverter esse patch.

```python
# tests/conftest.py
import slowapi
slowapi.Limiter.limit = _noop_limit
```

---

### 8. Tests — Env Vars Default

**Sintoma**: `Settings()` falha em testes com "SECRET_KEY inválida" ao importar `app.core.config`.

**Causa**: `Settings()` valida `SECRET_KEY` no construtor. Sem `.env`, falta a variável.

**Solução**: `tests/conftest.py` faz `os.environ.setdefault(...)` pras 4 envs obrigatórias **antes** de qualquer import que carregue config. Aplicado em module-level no topo do conftest.

**Implicação**: Testes que queiram validar comportamento de "SECRET_KEY ausente" devem usar `monkeypatch.delenv("SECRET_KEY")`.

---

## Comportamentos Contra-Intuitivos

### 1. Datetime - UTC vs Local

**O que parece**: O código usa `datetime.now()` normalmente.

**O que realmente acontece**: O código mistura `datetime.utcnow()` (naive) e `datetime.now(timezone.utc)` (aware).

**Por quê**: O banco usa `TIMESTAMP WITHOUT TIME ZONE`, incompatível com datetimes aware.

**Implicações**:
- Sempre use `datetime.utcnow()` para operações de banco
- JWT tokens usam `timezone.utc` (correto)
- Limite diário reseta em **meia-noite UTC**, não local

**Arquivos afetados**:
- `app/db/models.py` (linha 12-14) - naive
- `app/services/automation/news_pipeline.py` (linhas 255-273) - naive para banco
- `app/core/security.py` (linhas 25-27) - aware para JWT

---

### 2. Guardrails NFA - Warning, Não Bloqueio

**O que parece**: Conteúdo com frases proibidas de NFA seria bloqueado.

**O que realmente acontece**: Frases proibidas geram **warning no log**, mas conteúdo é **publicado**.

**Por quê**: É preferível publicar e revisar depois do que perder conteúdo válido por falso positivo.

**Implicações**:
- Monitore logs para `[NFA Warning]`
- Considere revisão manual para posts flagados
- Guardrails são *sugestões*, não *bloqueios*

---

### 3. Frontend Revalidation - Falha Silenciosa

**O que parece**: Webhook de revalidação é crítico para o ISR funcionar.

**O que realmente acontece**: Se o webhook falhar, o log registra warning e a execução continua.

**Por quê**: Falha de revalidação não deve impedir publicação de conteúdo.

**Implicações**:
- Posts podem estar publicados no banco mas não visíveis no frontend
- Verifique logs para `[Revalidation failed]`
- Cache do frontend pode estar desatualizado

**Arquivo**: `app/services/automation/news_pipeline.py` (linhas 275-296)

---

### 4. Categorização - Fallback para Default

**O que parece**: Toda notícia deve ter uma categoria específica atribuída.

**O que realmente acontece**: Se a classificação falhar, usa tom `"default"` (genérico).

**Por quê**: Melhor publicar com tom genérico do que não publicar.

**Implicações**:
- Alguns posts podem ter tom inconsistente
- Revise posts sem categoria específica periodicamente

---

## Workarounds e Soluções Temporárias

### 1. Double Base64 Gemini Images

**Problema Original**: Gemini às vezes retorna dados de imagem double-encoded em base64.

**Solução Aplicada**: Detecção automática e decodificação dupla quando necessário.

**Localização**: `app/services/ai/image_generator.py` (linhas 313-330)

**Status**: Permanente (bug do SDK, não do código)

**Cuidados**: Não remover a lógica de detecção mesmo que pareça "hacky".

```python
# O código verifica se os primeiros bytes parecem base64
first_chars = first_bytes.decode('ascii')
if all(c in 'ABCDEF...=' for c in first_chars):
    # É double-encoded, decodifica novamente
    image_bytes = base64.b64decode(image_bytes)
```

---

### 2. Pillow Validation Bypass

**Problema Original**: Nem todos os formatos de imagem do Gemini são validáveis pelo Pillow.

**Solução Aplicada**: Se Pillow falhar, faz upload direto para Cloudinary sem validação.

**Localização**: `app/services/ai/image_generator.py` (linhas 450-454)

**Status**: Permanente (limitação de formatos suportados)

**Cuidados**: Cloudinary pode rejeitar imagens inválidas; monitore erros de upload.

---

## Dependências de Ordem e Sequência

### 1. Middleware Order em FastAPI

**Contexto**: Setup de middlewares em `app/main.py`

**Ordem Necessária**:
1. Rate limiting (primeiro)
2. CORS
3. Request context
4. Exception handlers

**Consequência se Ignorado**: Rate limiting pode não funcionar corretamente.

**Código**:
```python
# app/main.py linha 46-47
# Rate limiting (deve vir antes dos outros middlewares)
setup_rate_limiting(app)
```

---

### 2. Migrations Antes do Start

**Contexto**: O servidor depende do schema do banco estar atualizado.

**Ordem Necessária**:
1. `alembic upgrade head`
2. `uvicorn app.main:app`

**Consequência se Ignorado**: Erros de colunas/tabelas inexistentes.

**Script**: `start.sh` já faz isso automaticamente.

---

### 3. Configuração de Ambiente Antes de Testes

**Contexto**: Testes precisam de variáveis mínimas configuradas.

**Ordem Necessária**:
1. Copiar `.env.example` para `.env`
2. Preencher pelo menos `SECRET_KEY`
3. Executar `pytest`

**Consequência se Ignorado**: Testes falham com erro de validação de config.

---

## Configurações Não-Óbvias

### 1. `DB_POOL_RECYCLE = 1800`

**Configuração**: Conexões são recicladas após 30 minutos

**Por que parece errado**: Por que não manter conexões indefinidamente?

**Por que está certo**: Evita conexões stale após timeouts do PostgreSQL ou reinícios do banco.

---

### 2. `pool_pre_ping = True`

**Configuração**: Testa conexões antes de usar

**Por que parece errado**: Overhead adicional em cada query

**Por que está certo**: Previne erros de "connection already closed" em produção

---

### 3. CORS sem `PATCH`

**Configuração**: Métodos permitidos: GET, POST, PUT, DELETE, OPTIONS

**Por que parece errado**: PATCH é comum para updates parciais

**Por que está certo**: A API usa PUT para todos os updates; PATCH não é usado

---

## Débitos Técnicos Conhecidos

### 1. Mistura de Datetime Patterns

**Descrição**: Código usa tanto `datetime.utcnow()` quanto `datetime.now(timezone.utc)`

**Impacto**: Potencial para bugs de comparação de timezone

**Origem**: Evolução orgânica do código

**Plano**: Padronizar para `datetime.utcnow()` em operações de banco

---

### 2. Sem Linter Configurado

**Descrição**: Não há `ruff`, `black`, ou `isort` configurado

**Impacto**: Inconsistência de formatação entre desenvolvedores

**Origem**: Setup inicial sem CI/CD

**Plano**: Adicionar `ruff` ou `black` com pre-commit hooks

---

### 3. Cobertura de Testes Parcial

**Descrição**: ~1958 linhas de testes para ~8782 linhas de código

**Impacto**: Alguns serviços de IA não têm testes unitários

**Origem**: Serviços de IA são difíceis de testar sem mocks extensivos

**Plano**: Aumentar cobertura com mocks de APIs externas

---

## Dicas de Desenvolvimento

### Ambiente Local

```bash
# 1. Clone e configure
git clone <repo>
cd verticecripto-backend
cp .env.example .env

# 2. Edite .env com chaves de API reais
# Mínimo necessário:
# - DATABASE_URL (pode usar SQLite para testes)
# - SECRET_KEY (32+ chars)
# - GEMINI_API_KEY (para gerar conteúdo)
# - OPENAI_API_KEY (fallback)
# - CLOUDINARY_* (para imagens)

# 3. Instale dependências
pip install -r requirements.txt

# 4. Execute migrations
alembic upgrade head

# 5. Inicie o servidor
uvicorn app.main:app --reload

# 6. Teste a API
curl http://localhost:8000/health
```

### Debugging

```bash
# Ver logs do pipeline
grep -E "(Pipeline|ContentGen|ImageGen|Dedup)" logs/app.log

# Verificar fallbacks de AI
grep "trying OpenAI\|falling back" logs/app.log

# Verificar deduplicação
grep "Similarity:" logs/app.log

# Verificar rate limiting
grep "rate limit" logs/app.log
```

### Performance

**Evitar**:
- Não chamar `/automation/trigger` mais de 5x/minuto (rate limited)
- Não desabilitar cache de embeddings em produção
- Não aumentar `POSTS_PER_EXECUTION` muito (custos de API)

**Otimizar**:
- Use Redis em produção para cache
- Configure `DAILY_POST_LIMIT` baseado em orçamento de API
- Monitore métricas de pipeline para identificar gargalos

### Testes

```bash
# Rodar todos os testes
pytest

# Com coverage
pytest --cov=app

# Apenas testes unitários
pytest tests/unit/

# Apenas testes de integração
pytest tests/integration/

# Teste específico
pytest tests/unit/test_crud_post.py -v

# Com output detalhado
pytest -v --tb=short
```

**Dica**: Testes usam SQLite em memória, não precisa de PostgreSQL local.

---

## O Que Eu Gostaria de Ter Sabido

1. **Configure Gemini primeiro**: É mais barato que OpenAI e deve ser o primário. Teste a chave antes de deploy.

2. **Redis não é opcional em produção**: Funciona sem, mas performance de deduplicação cai drasticamente.

3. **O limite diário é por UTC**: Se você está em BRT (UTC-3), o dia "vira" às 21h horário de Brasília.

4. **Fallbacks são silenciosos**: Se sua conta Gemini estiver com problema, você só descobre quando vê a fatura do OpenAI.

5. **Guardrails de NFA são warnings**: O conteúdo é publicado mesmo com flags; monitore os logs.

6. **O frontend precisa do webhook funcionando**: ISR não atualiza automaticamente; depende do `/api/revalidate`.

7. **Deduplicação com threshold 0.80 é conservadora**: Se muitas notícias únicas estão sendo rejeitadas, experimente 0.75.

8. **Railway tem CRON limitado**: Configure execuções algumas vezes ao dia, não a cada 30 minutos, para evitar custos extras.

9. **Sempre teste com `DEBUG=false` antes de deploy**: Validações de segurança só rodam em produção.

10. **Os comentários no código estão em português**: Toda a lógica de negócio está bem documentada nos próprios arquivos.

---

## Decisão pendente: o que `UPDATE_EXISTING` deveria fazer

Quando o `DuplicateDetector` decide `UPDATE_EXISTING`, o caminho vivo
(`ArticlePublisher.update_article`) **sobrescreve** o corpo do post com o
artigo novo. Não mescla, não guarda histórico.

O código continha uma implementação alternativa, mais rica, em
`DuplicateDetector.process_assignment` — método sem nenhum consumidor, removido
em 2026-07-26. O que ela fazia, registrado aqui porque a decisão de qual
comportamento é o certo continua aberta:

1. **Anexava com marcador de fonte** em vez de sobrescrever:
   `conteudo += f"\n\n[Atualização - {fonte}]\n{novo_conteudo}"`
2. **Guardava histórico** em `historico_atualizacoes`: timestamp, tipo da
   atualização, conteúdo adicionado, fonte e resumo da mudança. O campo NÃO
   existe no modelo do banco — `deduplication/repository.py` tem o comentário
   "Será implementado quando o campo for adicionado ao modelo".
3. **Tinha guarda de idempotência**: só anexava se o conteúdo novo já não
   estivesse presente.

**Nenhuma das duas abordagens é claramente melhor:**

| | Sobrescrever (vivo) | Anexar (intenção original) |
|---|---|---|
| Resultado | um artigo coerente | dois artigos de 700-1500 palavras concatenados |
| Perda | o texto original é destruído | nada se perde |
| Problema | perde a cobertura anterior | redundante, e estoura o limite de 1500 palavras do validador — que não é reexecutado em update |

Uma terceira via seria regerar um artigo mesclado, ao custo de mais uma chamada
de LLM.

**Ao decidir, considere junto:** em 2026-08-15 o threshold do detector foi
recalibrado de 0.80 (morto) para 0.55 (ver a seção sobre isso), então o
caminho de update passou a rodar de verdade — para pares quase idênticos
(≥0.55; duplicata real medida pontua 0.72+). O comportamento vivo de
sobrescrever ficou: `update_article` hoje atualiza título, corpo, excerpt e
meta juntos (coerente), preservando o slug. A escolha
sobrescrever/anexar/mesclar segue aberta, mas o cenário que a torna aceitável
— só disparar em releitura do mesmo fato — está travado por teste
(`test_mesma_historia_com_angulo_proprio_vira_post_novo`).

## Filtro de relevância: duas armadilhas de vocabulário

`app/services/sources/relevance_filter.py` descarta notícia quando há sinal de
outra editoria (`OFF_BEAT_PATTERNS`) e **não** há sinal de cripto
(`CRYPTO_SIGNAL_PATTERNS`). Duas regras não são óbvias e custaram uma rodada de
medição cada.

**1. Nunca ponha palavra genérica de negócios no veto.**

A primeira versão tinha `hack` na `CRYPTO_SIGNAL_PATTERNS`. Resultado:

    título: Nvidia, Meta, and Microsoft Tell Washington: Don't Kill Open-Source AI
    resumo: ...days after a Chinese AI helped Hugging Face survive a hack...

casou `Nvidia` e `Open-Source AI` na OFF_BEAT, e mesmo assim passou — uma
palavra que qualquer setor usa anulou dois sinais corretos. Também proibidos:
`protocol`, `exchange`, `treasury`, `node`, `bridge`, `ledger`, `circle`, `ada`.

**2. Não ponha substantivo geral de tecnologia na `OFF_BEAT_PATTERNS`.**

Esta é a mesma classe de erro da regra 1, na lista onde o custo é **descartar**
em vez de deixar passar — ou seja, a direção cara. A lista já teve `nvidia`,
`gpus?`, `data ?centers?`, `benchmarks?`, `quantum comput`, `robots?` e
`self-driving`. Ablação leave-one-out contra o feed vivo: os sete custavam
**zero** descartes, juntos ou separados, e derrubavam notícia legítima:

    data center  ->  Riot Platforms converts Texas data center to high-performance compute
    data center  ->  Hut 8 announces 300MW data center expansion in Alberta
    benchmark    ->  Fed holds benchmark rate steady as risk assets rally
    GPU          ->  A16z leads round in decentralized GPU marketplace

Riot e Hut 8 são mineradores de bitcoin. O pivô de minerador para data center
de IA é pauta central de negócio cripto, e esses títulos não carregam nenhum
termo do veto — então o veto não salva. O item equivalente do Galaxy sobrevivia
só porque `galaxy` por acaso estava na lista de cripto: frágil por acidente, não
por desenho.

**O critério da `OFF_BEAT_PATTERNS` é: nome próprio de laboratório ou modelo de
IA, ou jargão específico de IA. Nunca substantivo que cripto também usa.**

**3. Não use `\bai\b` solto na lista de outra editoria.**

Matéria de cripto cita IA o tempo todo ("Is the AI-to-crypto rotation
underway?", "Franklin Templeton Says Agentic AI Is Crypto's Killer Use Case").
Um padrão largo aí faz todo o resultado depender do veto. A forma correta de
cobrir contexto de IA é **nome próprio** de laboratório ou modelo — foi o que
resolveu "Chinese AI ... Chinese model GLM 5.2", que não casava com jargão
nenhum.

Medido: dos 9 itens de fronteira, **8 passam porque a `OFF_BEAT` nem dispara**;
só um depende do veto. O veto é rede de segurança estreita, não o mecanismo
principal — alargar a `OFF_BEAT` confiando no veto para compensar inverte isso
e é o caminho mais provável para o filtro começar a comer notícia legítima.

**Fronteira editorial:** o critério é o **sujeito** da notícia. Empresa de
cripto tratando de IA é pauta (Galaxy construindo data center, tesouraria em
bitcoin pivotando para IA, Worldcoin). Os testes em
`tests/unit/test_relevance_filter.py::test_nao_descarta_noticia_do_tema` travam
essa decisão. Se eles reclamarem depois de um ajuste de vocabulário, o
vocabulário é que está errado.

**Falha abre, em dois níveis.** Exceção dentro de `rejection_reason` deixa a
notícia passar; vocabulário que não compila desativa o filtro inteiro em vez de
derrubar a construção do `NewsAggregator` — que levaria o pipeline junto. O
guard captura `Exception`, e não só `re.error`, porque um item não-string na
tupla faz `"|".join()` levantar `TypeError`, que é o erro de digitação mais
provável.

**`rejection_reason` devolve `Optional[str]`, e `None` significa MANTER.**
Teste sempre com `is None`, nunca por veracidade: vocabulário vazio compila
para uma regex de largura zero e o método pode devolver `''`.

**Ao mexer no vocabulário:** rode o filtro contra o feed vivo e confira cada
descarte na mão. Lista de palavras não se escreve por suposição.

    python3 -c "
    import asyncio, sys; sys.path.insert(0,'.')
    from app.services.sources.news_aggregator import NewsAggregator
    agg = NewsAggregator()
    itens = asyncio.run(agg.rss_collector.collect_all(hours_back=72))
    agg._filter_off_topic(itens)"

A taxa esperada fica entre 3% e 10% (medido: 4 de 87 e 7 de 110). Acima de 15%
quase certamente indica padrão largo demais na `OFF_BEAT_PATTERNS`.

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

### `context_filter` sobrescreve `bind()`, e isso é de propósito

`context_filter` faz atribuição incondicional, não `setdefault`:

    record["extra"]["request_id"] = get_request_id() or "-"

Trocar por `setdefault` parece inofensivo e é tentador — durante este trabalho a
troca foi feita justamente para tornar um teste de fallback alcançável, já que o
filtro sobrescreve qualquer `logger.bind(request_id=...)` antes do sink rodar.

Foi revertido. O contextvar é a fonte da verdade porque quem o popula é o
middleware de requisição; um call site capaz de sobrepô-lo via `bind` viraria
armadilha — bastaria alguém "ajudar" ligando um ID conhecido localmente para
mascarar o ID real da requisição. `test_context_filter_tem_precedencia_sobre_bind`
trava esse comportamento.

A lição mais geral: o teste é que estava errado. Para exercitar o fallback do
sink, chame `_json_sink` direto com um record montado à mão, como faz
`test_registro_nao_serializavel_ainda_produz_linha`. Não afrouxe produção para
alcançar um caminho de teste.

**Ainda em aberto:** `LogContext` e `log_operation` (mesmo arquivo) não são
usados em lugar nenhum do projeto, e o contexto estruturado que adicionam seria
descartado de qualquer forma — o sink só lê `request_id` e `correlation_id` de
`extra`. Decidir entre remover ou fazer funcionar.

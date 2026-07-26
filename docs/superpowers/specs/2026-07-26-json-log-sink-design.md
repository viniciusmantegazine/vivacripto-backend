# Sink JSON de produção que não quebra

**Data:** 2026-07-26
**Status:** aprovado, pronto para plano de implementação

## Problema

`app/core/logging.py:82-98` monta o JSON de produção por interpolação de string:

```python
log_format = (
    '{{"timestamp":"{time:YYYY-MM-DDTHH:mm:ss.SSSZ}",'
    ...
    '"message":"{message}"}}'
)
logger.add(sys.stderr, format=log_format, level="INFO", filter=context_filter, serialize=False)
```

`{message}` entra cru dentro de aspas. Qualquer mensagem contendo `"`, `\` ou
quebra de linha produz uma linha que o agregador não consegue parsear. Medido:

```
titulo com aspas duplas      JSON QUEBRADO -> Expecting ',' delimiter
titulo com barra invertida   JSON QUEBRADO -> Invalid \escape
titulo com quebra de linha   JSON QUEBRADO -> Invalid control character
```

`DEBUG` é `False` por padrão (`app/core/config.py:24`) e `setup_logging()` roda
em `app/main.py:21`, então este é o caminho de produção.

### Segundo modo de falha: `logger.exception`

Com `format=` e sem `serialize`, o loguru anexa o traceback **depois** da linha
formatada, fora do objeto JSON:

```
{"timestamp":"19:39:22","level":"ERROR","message":"Falhou: quebra "aqui""}
Traceback (most recent call last):
  File "<stdin>", line 8, in <module>
ValueError: quebra "aqui"
```

Uma linha quebrada seguida de quatro linhas que não são JSON nenhum.

### Tamanho do problema

| | |
|---|---|
| 5 chamadas fazem `logger.error(f"Traceback: {traceback.format_exc()}")` | multi-linha, JSON **sempre** quebrado |
| 76 chamadas interpolam `{e}` em `error`/`warning`/`exception` | texto de exceção traz aspas com frequência |
| 418 chamadas de log no total | qualquer `"`, `\` ou `\n` quebra a linha |

O efeito prático é que o log de produção fica ilegível para o agregador
exatamente quando algo dá errado — os cinco tracebacks falham em 100% dos casos.

### Por que agora

O filtro de relevância recém-entregue apoia toda a sua garantia de
observabilidade em linhas de WARNING serem consultáveis no agregador. Esse
argumento não se sustenta enquanto o sink puder emitir linha inválida. O bug é
anterior ao filtro e afeta o projeto inteiro; o filtro só tornou a dependência
explícita.

## Decisões

| Questão | Decisão | Razão |
|---|---|---|
| Mecanismo | Sink callable que monta `dict` e passa por `json.dumps` | Escapa por construção e preserva os nomes de campo atuais |
| `serialize=True` | Descartado | Corrige o escape mas aninha tudo sob `record` e move a mensagem; quebra qualquer query existente no agregador |
| Escape na format-string | Impossível | O loguru não tem filtro de escape em formato |
| Traceback | Campo `exception` no mesmo objeto | Hoje sai em linhas soltas fora do JSON |
| Os 5 `logger.error(f"Traceback: ...")` | Fora de escopo | Com o sink correto passam a funcionar sozinhos; converter mexeria em dois outros arquivos e quebraria quem faz grep por `"Traceback:"` |

## Contrato que NÃO pode mudar

Os nomes e tipos de campo atuais são o contrato com o agregador. O sink novo
tem de produzir exatamente as mesmas chaves:

| Campo | Tipo | Origem no record |
|---|---|---|
| `timestamp` | string | `record["time"].isoformat(timespec="milliseconds")` |
| `level` | string | `record["level"].name` |
| `request_id` | string | `record["extra"]["request_id"]` |
| `correlation_id` | string | `record["extra"]["correlation_id"]` |
| `logger` | string | `record["name"]` |
| `function` | string | `record["function"]` |
| `line` | **número**, não string | `record["line"]` |
| `message` | string | `record["message"]` |

**O timestamp é o detalhe fácil de errar.** O formato atual
`{time:YYYY-MM-DDTHH:mm:ss.SSSZ}` produz `2026-07-26T19:40:34.148-03:00`, com
dois-pontos no offset. Reconstruir com `strftime("%z")` daria `-0300`, **sem**
dois-pontos — uma mudança silenciosa de contrato. Medido:
`isoformat(timespec="milliseconds")` reproduz a saída atual byte a byte.

`line` hoje é emitido sem aspas (`'"line":{line},'`). Tem de continuar número.

**O `filter=context_filter` tem de continuar anexado ao handler.** É ele que
popula `record["extra"]["request_id"]` e `record["extra"]["correlation_id"]`
(`app/core/logging.py:43-47`); sem ele o sink leria chaves inexistentes e os
dois campos sumiriam do contrato. Ler com `.get(..., "-")` é a rede de
segurança, não a solução.

## Componente

Uma função de sink em `app/core/logging.py`, usada no lugar da format-string:

```python
def _json_sink(message) -> None:
    """Escreve o record como uma linha de JSON válido em stderr."""
```

O loguru entrega um objeto `Message` (subclasse de `str`) com `.record`. O sink
lê o record, monta o dict e escreve `json.dumps(payload) + "\n"` em
`sys.stderr`.

### Campo `exception`

`record["exception"]` é `None` ou uma tupla nomeada `(type, value, traceback)`.
Quando presente, o sink acrescenta uma chave `exception` com o traceback
formatado como **uma string** — escapada pelo `json.dumps`, portanto dentro do
objeto. Quando ausente, a chave não aparece, para não poluir a linha comum.

### Falha do próprio sink

Quando um sink levanta exceção, o loguru captura, escreve um bloco
`--- Logging error in Loguru Handler ---` em stderr contendo o record, e segue.
Medido: o conteúdo da mensagem não some, mas a **linha estruturada** sim — o que
chega ao agregador é um bloco multi-linha não parseável, exatamente o problema
que este trabalho existe para eliminar.

Como este sink é a única saída estruturada de produção, ele não pode perder log:
`json.dumps` roda com `default=str`, e o corpo inteiro fica dentro de
`try`/`except`. Se ainda assim falhar, o `except` emite uma linha JSON mínima
construída apenas com literais seguros, contendo o nível e o `repr` do erro de
serialização. Perder a estrutura de uma linha é aceitável; perder a linha não é.

## Testes

Sem rede, sem escrever em arquivo. O sink é uma função pura sobre um record, o
que torna o teste direto: instala-se o sink apontando para uma lista, emite-se
o log e faz-se `json.loads` da saída.

**Escape** — mensagem com `"`, com `\`, com quebra de linha, e com as três
juntas: cada uma tem de produzir `json.loads` bem-sucedido e `payload["message"]`
igual ao texto original.

**Contrato de campos** — as oito chaves presentes, com os nomes exatos, e
`payload["line"]` sendo `int` e não `str`.

**Timestamp** — igualdade com a saída de um sink paralelo usando o formato
antigo `{time:YYYY-MM-DDTHH:mm:ss.SSSZ}`. É o teste que pega a regressão de
`-03:00` para `-0300`.

**Exceção** — `logger.exception` dentro de um `except` produz **uma única
linha**, com `json.loads` bem-sucedido, contendo `exception` com o nome do tipo
e a mensagem do erro. Este é o teste que trava a correção do segundo modo de
falha: hoje a mesma chamada emite várias linhas — quantas depende da
profundidade da pilha — e só a primeira tenta ser JSON.

**Sem exceção** — a chave `exception` não aparece.

**Falha na serialização** — record com `extra` não serializável não pode
derrubar o sink nem sumir com a linha.

**Regressão dos casos reais** — os títulos de notícia usados como mensagem, com
aspas retas, têm de sair parseáveis. É o caso que motivou o trabalho.

## Fora de escopo

- **Os 5 `logger.error(f"Traceback: {traceback.format_exc()}")`.** Passam a
  funcionar com o sink correto (viram uma string escapada em `message`).
  Continuam gerando duas linhas por erro; consolidar é decisão separada.
- **`LogContext` e `log_operation`** (`app/core/logging.py:113-209`). Não são
  usados em lugar nenhum do projeto, e o contexto estruturado que adicionam
  seria descartado de qualquer forma, porque o formato só lê `extra[request_id]`
  e `extra[correlation_id]`. Decidir depois entre remover ou fazer funcionar;
  misturar aqui alarga o escopo.
- **O sink de arquivo** `logs/error.log` (`app/core/logging.py:101-108`). É
  texto puro, não JSON, e não sofre do problema.
- **O sink de desenvolvimento.** Formato colorido para humano, sem JSON.

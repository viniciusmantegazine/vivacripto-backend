# Fronteira de palavra na remoção de nomes de veículos — Design

**Data:** 2026-07-26
**Escopo:** `_sanitize_content` em `app/services/ai/content_generator.py`
**Tipo:** correção de bug em produção (corrupção de conteúdo publicado)

## Problema

`_sanitize_content` remove menções a veículos jornalísticos concorrentes do texto gerado pelo LLM. A lista de nomes inclui variantes em minúscula (`"decrypt"`, `"the block"`), e tanto o **gatilho** quanto a **remoção final** operam por substring:

```python
for site_name in source_site_names:      # linha 647
    if site_name in result:              # gatilho: substring
        logger.error("[Sanitização CRÍTICA] ...")   # linha 650
        # ... dois regexes de frase atributiva (corretos) ...
        if site_name in result:          # linha 666
            result = result.replace(site_name, "")  # linha 667: substring
```

Como `"decrypted"` contém `"decrypt"` e `"the blockchain"` contém `"the block"`, vocabulário técnico normal é tratado como nome de veículo.

### Consequência 1 — corrupção de artigo publicado

Medido no código atual:

| Entrada | Saída |
|---|---|
| `A transação foi decrypted pelo protocolo.` | `A transação foi ed pelo protocolo.` |
| `O processo de decryption garante privacidade.` | `O processo de ion garante privacidade.` |
| `Dados via the blockchain publica.` | `Dados via chain publica.` |
| `Analistas avaliam the block height atual.` | `Analistas avaliam height atual.` |

`"blockchain"` isolado sobrevive (não contém `"the block"`), mas a construção `"the blockchain"` não.

### Consequência 2 — log CRÍTICO falso

O gatilho é a mesma checagem de substring, então cada ocorrência de `"decrypted"` emite

```
[Sanitização CRÍTICA] LLM violou regra e citou veículo 'decrypt'. Removendo frase atributiva. Revisar prompt se reincidir.
```

O LLM não violou nada. O log existe para detectar violação real de prompt, e esse ruído destrói sua utilidade — quem monitorar vai aprender a ignorar a mensagem.

### Medição

Sobre os 4 casos de corrupção acima, mais 5 casos que devem passar intactos e 4 citações reais de veículo:

| Abordagem | Corrupções corrigidas | Citações reais pegas |
|---|---|---|
| Atual (substring) | 0 de 4 | 4 de 4 |
| `\b` + `re.I` em tudo | **3** de 4 | 4 de 4 |
| `\b` + `re.I`, com `The Block` case-sensitive | **4** de 4 | 4 de 4 |

Fronteira de palavra sozinha não resolve `the block height`: `\bthe block\b` casa com a frase inglesa exatamente como casa com o nome do veículo. A distinção é a caixa — ver a decisão abaixo.

Citação em minúscula (`segundo o cointelegraph`) continua sendo pega em todas as abordagens, porque só `The Block` fica case-sensitive.

## Decisões

| Questão | Decisão | Razão |
|---|---|---|
| Gatilho | `re.search(rf'\b{re.escape(nome)}\b', result, re.I)` | Corrige a corrupção e o log falso de uma vez — é a mesma checagem |
| Remoção final | `re.sub(rf'\b{re.escape(nome)}\b', '', result, flags=re.I)` | Substring é o que quebra as palavras |
| Lista de nomes | Colapsar de 24 para 11 entradas canônicas | As variantes de caixa existem só porque o `.replace()` é case-sensitive; com `re.I` viram redundância |
| Sensibilidade a caixa | Case-**insensitive**, exceto `The Block` | Citação em minúscula é padrão real (`segundo o cointelegraph`), então o default é insensível. `The Block` é a exceção: ver abaixo |
| Os dois regexes de frase atributiva | Manter como estão | Já têm `\b` e funcionam. Só o gatilho e a remoção final estão quebrados |

### Lista canônica (11 entradas)

```
CoinDesk, CoinTelegraph, CryptoSlate, Bitcoin Magazine, Decrypt,
The Block, CoinPaper, CoinRepo, BeInCrypto, NewsBTC, CryptoNews
```

`"CoinTelegraph"` e `"Cointelegraph"` colapsam numa entrada porque diferem apenas na caixa do T, que `re.I` cobre.

### Por que `The Block` é exceção

Dois nomes da lista também são palavras comuns em inglês, mas com frequências muito diferentes em texto sobre cripto:

| Nome | Colisão | Frequência |
|---|---|---|
| `The Block` | `the block height`, `the block reward`, `the block size` | **alta** — vocabulário central de mineração e rede |
| `Decrypt` | `decrypt` como verbo | baixa — em português o verbo é "descriptografar" |

`The Block` casa case-sensitive; o resto da lista continua insensível. Isso preserva `the block height` intacto e continua removendo `The Block informou que...`, porque LLM escreve nome próprio com maiúscula.

A estrutura na implementação é uma exceção declarada por nome, não um flag por entrada — mantém a lista legível e deixa explícito que há exatamente um caso especial e por quê.

## Resíduo aceito

Duas limitações conhecidas, ambas de baixa frequência:

1. **Verbo `decrypt` isolado** — `"é preciso decrypt os dados"` dispara e é removido. Não vale tornar `Decrypt` case-sensitive: a colisão é rara em texto PT, e perderíamos `segundo o decrypt` em minúscula.
2. **`The Block` em minúscula como veículo** — `"segundo o the block"` passa a escapar. É o custo direto da decisão acima, e o menos provável dos dois: nome próprio em texto gerado por LLM vem capitalizado.

Ficam registradas como limitação conhecida, não como defeito aberto.

## Fora de escopo (deliberado)

- **Consolidar as 3 chamadas de LLM em 1.** É o próximo sub-projeto, com spec próprio. Toca `generate_article` e os métodos `_generate_*`; este bug vive em `_sanitize_content`. Sem conflito.
- **`temperature` nas chamadas de título/meta.** Dissolve-se na consolidação: aquelas chamadas deixam de existir. Não faz sentido corrigir algo que vai ser removido.
- **Artefatos de pontuação órfã.** Remover `"CoinDesk"` de `"o CoinDesk's relatório"` deixa `"'s"`. A limpeza existente já trata espaço duplo e vírgula órfã; possessivo em inglês é raro em texto PT e não justifica regex nova aqui.
- **Corrigir a contagem "4 chamadas de LLM" no comentário do `news_pipeline.py`.** São 3. É uma imprecisão minha, commitada na primeira rodada. Vai junto no spec da consolidação, onde o número é o assunto.

## Estratégia de teste

Testes novos em `tests/unit/test_content_generator_sanitize_boundary.py`, sem rede e sem LLM (`_sanitize_content` é síncrono e puro).

1. **Vocabulário técnico sai intacto** — parametrizado sobre os 4 casos de corrupção medidos: `decrypted`, `decryption`, `the blockchain`, `the block height`. Este é o teste que prova o bug corrigido. `the block height` só passa por causa da exceção case-sensitive, então ele cobre as duas decisões de uma vez.
2. **Citação real de veículo continua sendo removida** — parametrizado sobre `Segundo o CoinDesk`, `The Block informou que`, `Conforme o Decrypt`, e a variante minúscula `segundo o cointelegraph`.
3. **Provedores de dados não são tocados** — `CoinGecko`, `Glassnode` e afins são explicitamente permitidos pelo prompt; garantir que não entraram na lista por engano.
4. **A lista não tem duplicata de caixa** — impede que alguém reintroduza `"coindesk"` ao lado de `"CoinDesk"` e ressuscite a confusão que motivou o bug.
5. **A exceção case-sensitive está documentada em teste** — asserção de que `The Block` está no conjunto de exceções e que `CoinDesk` não está, para que a exceção não seja removida por engano num refactor futuro nem estendida sem intenção.

Baseline atual: `335 passed, 0 failed, 0 errors`. Os testes existentes de `test_content_generator_sanitize.py` devem continuar passando sem alteração — se algum quebrar, é sinal de que a mudança alterou comportamento além do pretendido e precisa ser investigado, não acomodado.

## Risco

Baixo. A mudança é localizada num único método síncrono, torna o comportamento **mais** conservador (remove menos), e é coberta por teste em ambas as direções — o que deve sair e o que deve ficar. O modo de falha plausível é uma citação de veículo que passe a escapar; a suíte cobre os quatro formatos conhecidos, incluindo minúscula.

# Migração dos modelos Claude do relatório semanal — Design

**Data:** 2026-07-26
**Escopo:** `app/services/ai/weekly_report_generator.py` e seus testes
**Tipo:** correção de bug em produção (não é feature)

## Problema

`WeeklyReportGenerator` chama a API da Anthropic com dois model IDs **depreciados**, tanto no primário quanto no fallback:

```python
CLAUDE_MODEL          = "claude-opus-4-20250514"
CLAUDE_FALLBACK_MODEL = "claude-sonnet-4-20250514"
```

A data de retirada documentada para `claude-opus-4-20250514` é **15/jun/2026** — 6 semanas antes desta data. O serviço está ligado a um endpoint vivo (`POST /api/v1/automation/weekly-report`, `app/api/v1/endpoints/automation.py:163`), e o fallback aponta para um modelo da mesma geração depreciada: quando o primário falha por ID inválido, o fallback falha pelo mesmo motivo. O resultado é `generate_report()` retornando `None` e o endpoint respondendo erro.

O arquivo tem **cobertura de teste zero**, que é por que isso passou despercebido.

Migrar para um modelo atual não é trocar a string: a rota `claude-opus-4-*` → geração atual atravessa cinco mudanças de comportamento, três delas capazes de gerar 400 ou crash.

### Os cinco defeitos

| # | Defeito | Local | Consequência |
|---|---|---|---|
| 1 | Model IDs depreciados (primário e fallback) | linhas 47-48 | Chamada rejeitada; fallback não salva |
| 2 | `temperature=0.7` | linhas 205, 225 | `temperature` foi **removido** nos modelos atuais → **HTTP 400** |
| 3 | `max_tokens=8192` | linha 51 | Nos modelos atuais o thinking vem ligado por padrão e **divide esse teto com o texto da resposta**. Relatório de 1500-3000 palavras trunca no meio |
| 4 | `response.content[0].text` | linhas 211, 231 | Com thinking ligado, `content[0]` é um bloco de thinking, não de texto → **crash (`AttributeError`) ou relatório vazio** |
| 5 | Sem tratamento de `stop_reason == "refusal"` | bloco de geração | Classificadores de segurança retornam **HTTP 200** com `content` vazio; o código trata como sucesso e devolve relatório vazio |

Os defeitos 3, 4 e 5 são **latentes**: não se manifestam hoje (os modelos antigos não ligam thinking por padrão nem têm classificador equivalente) e passam a valer no instante em que os IDs são atualizados. Corrigir só o item 1 troca uma falha por outra.

## Decisões

| Questão | Decisão | Razão |
|---|---|---|
| Modelo primário | `claude-opus-5` | Sucessor de tier para o Opus atual |
| Modelo de fallback | `claude-sonnet-5` | Preserva a intenção do código atual (Opus primário, Sonnet mais barato no fallback) |
| `temperature` | Remover; compensar com instrução de tom no prompt | O parâmetro não tem substituto nos modelos atuais. A intenção original ("um pouco mais criativo para análises") passa a viver no `WEEKLY_REPORT_SYSTEM_PROMPT` (texto proposto abaixo) |

### Instrução de tom que substitui o `temperature`

A ser adicionada ao `WEEKLY_REPORT_SYSTEM_PROMPT`. Traduz "temperature 0.7" em direção editorial explícita, em vez de deixar o tom ao acaso:

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

A última frase é deliberada: a diretriz de tom não pode abrir brecha nos guardrails de alucinação e NFA que o prompt já tem.
| `max_tokens` | `16000` | Um relatório de 3000 palavras em português consome ~4500 tokens; o resto é folga para o thinking, que agora divide o mesmo teto |
| Streaming | Adotar, com `.get_final_message()` | Independente do teto: relatório longo + thinking é o caso clássico de a requisição não-streaming estourar timeout de HTTP. O `.get_final_message()` mantém o código igual ao de hoje (uma resposta completa no fim), sem precisar tratar eventos |
| Leitura da resposta | Varrer `response.content` pelo bloco `type == "text"` | `content[0]` deixa de ser confiável quando há thinking |
| `stop_reason` | Checar antes de ler `content` | Recusa vem como HTTP 200, não como exceção |

## Fora de escopo (deliberado)

- **O `try/except` de fallback fica como está.** Existe um parâmetro `fallbacks` server-side, mas ele dispara **somente em recusa de política** — não em rate limit, overload ou erro de rede, que é o que o `except` atual cobre. Substituir um pelo outro perderia cobertura. Podem coexistir no futuro; não neste escopo.
- **`thinking` não será configurado explicitamente.** O padrão dos modelos escolhidos (ligado, adaptativo) é o desejado para análise semanal. Não há motivo para passar o parâmetro.
- **O conteúdo editorial do `WEEKLY_REPORT_SYSTEM_PROMPT` não muda**, além da adição da diretriz de tom que substitui o `temperature`.
- **Os outros serviços de IA não entram.** `content_generator.py` (Gemini/OpenAI) e `airdrop_post_generator.py` (`claude-sonnet-4-6`, ID atual e válido) estão fora. O `airdrop_post_generator.py` foi verificado e **não** tem esse problema.

## Estratégia de teste

O arquivo tem cobertura zero. Os testes novos usam mocks do cliente Anthropic — sem chamada de rede, sem credencial.

1. **Model IDs são atuais** — asserção sobre as constantes, para que uma futura depreciação seja pega por teste e não em produção.
2. **Nenhum parâmetro removido é enviado** — inspecionar os kwargs da chamada e garantir ausência de `temperature`, `top_p`, `top_k`. Este é o teste que impede a regressão do defeito 2.
3. **Extração de texto com thinking presente** — resposta mockada com um bloco de thinking em `content[0]` e o texto em `content[1]`; o gerador deve devolver o texto, não estourar.
4. **Recusa é tratada** — resposta mockada com `stop_reason="refusal"` e `content=[]`; o gerador deve retornar `None` e logar, em vez de devolver string vazia como sucesso.
5. **Fallback dispara em falha do primário** — primeira chamada levanta exceção, segunda devolve conteúdo; verificar que o modelo de fallback foi usado.
6. **`max_tokens` e streaming** — verificar que a chamada usa o caminho de streaming e o teto configurado.

Baseline atual: `321 passed, 0 failed, 0 errors`. Nenhum teste deve regredir.

## Verificação e sua limitação

**Não é possível confirmar localmente se os IDs antigos já foram retirados.** O ambiente não tem `ANTHROPIC_API_KEY`, não tem `.env` e não tem o CLI `ant` instalado. A confirmação via Models API (`client.models.retrieve`) precisa rodar onde há credencial — ambiente de deploy ou execução manual.

Isso **não bloqueia a correção**: os IDs estão documentadamente depreciados e os cinco defeitos acima valem independentemente da data exata de retirada. Mas significa que a validação final do endpoint em si é um passo pós-deploy, não algo que a suíte local prove.

Checklist de verificação:
- Suíte completa sem regressão (`321 passed` como piso)
- Os 6 testes novos passando
- Onde houver credencial: `client.models.retrieve("claude-opus-5")` responde, e o endpoint `POST /automation/weekly-report` gera relatório de ponta a ponta

## Risco

Baixo, com uma ressalva. O arquivo é isolado (um serviço, um endpoint, sem dependentes), a mudança é localizada e sai de um estado provavelmente já quebrado — o downside é limitado. A ressalva é que **a validação de ponta a ponta depende de credencial que não existe no ambiente local**, então o primeiro exercício real do caminho corrigido acontece no deploy.

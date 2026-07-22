# Arquitetura de Sistema de Detecção de Duplicatas - VerticeCripto

## 1. Visão Geral

O sistema de detecção de duplicatas é uma camada intermediária no pipeline de geração de notícias que previne a publicação de conteúdo duplicado através de análise de similaridade semântica.

## 2. Componentes Principais

### 2.1 Módulo de Similaridade Semântica
- **Responsabilidade**: Calcular similaridade entre textos
- **Estratégias**: 
  - Embeddings + Cosine Similarity (recomendado para produção)
  - Distância de Levenshtein (fallback simples)
  - Análise TF-IDF (alternativa intermediária)

### 2.2 Repositório de Posts
- **Responsabilidade**: Armazenar e recuperar posts publicados nas últimas 24h
- **Interface**: Suportar busca por timestamp e metadados

### 2.3 Orquestrador de Pipeline
- **Responsabilidade**: Coordenar fluxo de verificação e decisão
- **Lógica**: 
  1. Receber nova pauta
  2. Buscar posts similares (últimas 24h)
  3. Calcular similaridade
  4. Decidir: criar novo ou atualizar existente

### 2.4 Gerenciador de Atualizações
- **Responsabilidade**: Atualizar posts existentes com novas informações
- **Dados**: Timestamp de atualização, histórico de alterações

## 3. Fluxo de Dados

```
Nova Pauta (Título + Resumo)
    ↓
[Verificação de Similaridade]
    ↓
    ├─→ Similaridade > 80% → [Atualizar Post Existente]
    │                           ↓
    │                        Adicionar timestamp
    │                        Manter histórico
    │
    └─→ Similaridade ≤ 80% → [Criar Novo Post]
                                ↓
                            Publicar normalmente
```

## 4. Estrutura de Dados

### 4.1 Post Publicado
```json
{
  "id": "uuid",
  "titulo": "string",
  "resumo": "string",
  "conteudo": "string",
  "data_criacao": "ISO8601",
  "data_atualizacao": "ISO8601",
  "historico_atualizacoes": [
    {
      "timestamp": "ISO8601",
      "tipo_atualizacao": "nova_informacao|correcao",
      "conteudo_adicionado": "string"
    }
  ],
  "embedding": "vector[384-1536]",
  "tags": ["string"],
  "fonte": "string"
}
```

### 4.2 Pauta de Entrada
```json
{
  "titulo": "string",
  "resumo": "string",
  "conteudo": "string",
  "fonte": "string",
  "timestamp": "ISO8601"
}
```

### 4.3 Resultado de Verificação
```json
{
  "pauta_id": "string",
  "acao": "criar|atualizar",
  "post_existente_id": "uuid|null",
  "similaridade_maxima": "float[0-1]",
  "candidatos_similares": [
    {
      "post_id": "uuid",
      "titulo": "string",
      "similaridade": "float[0-1]"
    }
  ],
  "motivo": "string"
}
```

## 5. Critérios de Decisão

| Similaridade | Ação | Justificativa |
|---|---|---|
| > 80% | Atualizar | Conteúdo praticamente idêntico |
| 60-80% | Revisar manualmente | Conteúdo similar mas com nuances |
| < 60% | Criar novo | Conteúdo suficientemente diferente |

**Threshold configurável**: 80% é recomendado, mas pode ser ajustado via configuração.

## 6. Considerações de Performance

### 6.1 Otimizações
- Cache de embeddings para posts recentes
- Índice de busca por data para filtrar candidatos
- Busca aproximada (ANN) para grandes volumes
- Processamento assíncrono de embeddings

### 6.2 Escalabilidade
- Suporte para múltiplas fontes de notícias
- Processamento em lote (batch processing)
- Fila de processamento (ex: Celery, RabbitMQ)

## 7. Tratamento de Erros

| Cenário | Ação |
|---|---|
| Falha ao calcular embedding | Usar fallback (Levenshtein) |
| Banco de dados indisponível | Fila de retry com backoff exponencial |
| Timeout na verificação | Criar novo post (fail-safe) |

## 8. Monitoramento e Logging

- Métrica: Taxa de duplicatas detectadas
- Métrica: Tempo médio de verificação
- Métrica: Precisão do threshold
- Log: Cada decisão com score de similaridade
- Alerta: Anomalias na taxa de duplicatas

## 9. Roadmap de Implementação

### Fase 1 (MVP)
- Levenshtein + TF-IDF
- Banco de dados simples
- Threshold fixo de 80%

### Fase 2
- Integração com Embeddings (Sentence-Transformers)
- Cache de embeddings
- Dashboard de monitoramento

### Fase 3
- Machine Learning para ajuste dinâmico de threshold
- Análise de padrões de duplicatas
- Integração com sistema de recomendação

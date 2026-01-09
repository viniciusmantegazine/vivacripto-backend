# Guia Rápido de Implementação - Sistema de Detecção de Duplicatas

## Início Rápido

### 1. Instalação de Dependências

```bash
# Dependências básicas (já incluídas no Python 3.11)
# Para produção com embeddings (recomendado)
sudo pip3 install sentence-transformers
```

### 2. Estrutura de Dados Esperada

A pauta de entrada deve conter:

```python
{
    "titulo": "string",
    "resumo": "string", 
    "conteudo": "string",
    "fonte": "string",
    "timestamp": "ISO8601"
}
```

O post publicado no banco de dados deve conter:

```python
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
            "tipo_atualizacao": "nova_informacao",
            "conteudo_adicionado": "string",
            "fonte": "string"
        }
    ]
}
```

### 3. Integração ao Pipeline

```python
from duplicate_detector import PipelineOrchestrator, DuplicateDetector, NewsAssignment
from datetime import datetime

# Seu repositório customizado
from seu_modulo import SeuPostRepository

# Inicializar
repo = SeuPostRepository()
detector = DuplicateDetector(
    repository=repo,
    similarity_threshold=0.80,  # Ajuste conforme necessário
    engine_type="embedding"      # Use "embedding" em produção
)
orchestrator = PipelineOrchestrator(detector)

# Processar uma pauta
assignment = NewsAssignment(
    titulo="...",
    resumo="...",
    conteudo="...",
    fonte="...",
    timestamp=datetime.now().isoformat()
)

check_result, post = detector.process_assignment(assignment)

if check_result.acao.value == "criar":
    # Novo post criado
    print(f"Novo post: {post.id}")
elif check_result.acao.value == "atualizar":
    # Post atualizado
    print(f"Post atualizado: {post.id}")
```

### 4. Executar Testes

```bash
cd /home/ubuntu
python3.11 test_duplicate_detector.py
```

## Configuração de Thresholds

| Cenário | Threshold | Engine | Notas |
|---|---|---|---|
| Desenvolvimento | 0.40 | hybrid | Sem embeddings, mais permissivo |
| Staging | 0.60 | hybrid | Teste com dados reais |
| Produção (sem embeddings) | 0.50 | tfidf | Apenas TF-IDF |
| Produção (com embeddings) | 0.80 | embedding | Recomendado, mais preciso |

## Implementação do Repositório Customizado

```python
from duplicate_detector import PostRepository, PublishedPost
from datetime import datetime, timedelta

class MeuPostRepository(PostRepository):
    def __init__(self, db_connection):
        self.db = db_connection
    
    def get_posts_last_24h(self) -> list:
        cutoff = datetime.now() - timedelta(hours=24)
        return self.db.query(
            "SELECT * FROM posts WHERE data_criacao > ?",
            (cutoff.isoformat(),)
        )
    
    def get_post_by_id(self, post_id: str):
        return self.db.query_one(
            "SELECT * FROM posts WHERE id = ?",
            (post_id,)
        )
    
    def save_post(self, post: PublishedPost) -> str:
        self.db.execute(
            "INSERT INTO posts (...) VALUES (...)",
            (post.id, post.titulo, ...)
        )
        return post.id
    
    def update_post(self, post: PublishedPost) -> None:
        self.db.execute(
            "UPDATE posts SET ... WHERE id = ?",
            (post.id, ...)
        )
```

## Monitoramento

Registre as seguintes métricas:

- **Taxa de duplicatas detectadas**: Quantas pautas foram identificadas como duplicatas
- **Tempo médio de verificação**: Quanto tempo leva para verificar uma pauta
- **Distribuição de scores**: Histograma dos scores de similaridade
- **Erros de processamento**: Quantas pautas falharam

## Troubleshooting

### Erro: "sentence-transformers não instalado"
```bash
sudo pip3 install sentence-transformers
```

### Threshold muito alto (muitos falsos negativos)
Reduza o threshold de 0.80 para 0.70 ou 0.60.

### Threshold muito baixo (muitos falsos positivos)
Aumente o threshold ou use o engine "embedding" em vez de "hybrid".

### Desempenho lento
- Use cache de embeddings para posts recentes
- Implemente índice de busca (ex: FAISS) para grandes volumes
- Processe em lote com fila assíncrona (ex: Celery)

## Próximos Passos

1. Implementar `PostRepository` para seu banco de dados
2. Configurar logging e monitoramento
3. Testar com dados reais do VivaCripto
4. Ajustar thresholds com base em resultados
5. Considerar integração com ML para ajuste dinâmico

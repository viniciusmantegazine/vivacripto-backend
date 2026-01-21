# Documentação do VivaCripto Backend

## Visão Geral

O **VivaCripto Backend** é uma API de automação de conteúdo para o portal de notícias sobre criptomoedas VivaCripto. O sistema agrega notícias de múltiplas fontes, gera conteúdo em português usando IA (Google Gemini/OpenAI), cria imagens automaticamente, detecta duplicatas e publica artigos de forma totalmente automatizada.

**Tipo de Repositório**: Backend API / Microserviço de Automação de Conteúdo
**Linguagem Principal**: Python 3.11+
**Framework**: FastAPI
**Status**: Produção ativa

## Documentação Disponível

### Arquitetura e Stack
- [Stack Tecnológica](stack.md) - Tecnologias, frameworks e ferramentas utilizadas
- [Padrões de Design](patterns.md) - Padrões arquiteturais e de código

### Funcionalidades e Regras
- [Funcionalidades](features.md) - Descrição das funcionalidades principais
- [Regras de Negócio](business-rules.md) - Regras de negócio implementadas
- [Gotchas](gotchas.md) - Armadilhas, workarounds e conhecimento tácito

### Integrações
- [Integrações](integrations.md) - Comunicação com outros serviços e repositórios

### APIs e Serviços
- [Especificação de APIs](apis.md) - Endpoints, contratos e exemplos
- [Serviços Internos](services.md) - Arquitetura de serviços e responsabilidades

## Links Rápidos

| Recurso | Link/Comando |
|---------|--------------|
| Repositório Backend | `vivacripto-backend` |
| Repositório Frontend | `vivacripto-frontend` |
| Deploy | Railway (via git push) |
| Ambiente Local | `uvicorn app.main:app --reload` |
| Testes | `pytest` |
| Migrations | `alembic upgrade head` |

## Arquitetura de Alto Nível

```
┌─────────────────────────────────────────────────────────────────┐
│                     VivaCripto Backend                          │
│                        (FastAPI)                                │
└─────────────────────────────────────────────────────────────────┘
                              │
     ┌────────────────────────┼────────────────────────┐
     │                        │                        │
     ▼                        ▼                        ▼
┌─────────┐            ┌──────────┐             ┌──────────┐
│PostgreSQL│            │  Redis   │             │Cloudinary│
│(Database)│            │ (Cache)  │             │ (Images) │
└─────────┘            └──────────┘             └──────────┘

     RSS Feeds                AI Services              Frontend
         │                        │                        │
    ┌────▼────────────┐      ┌────▼─────────┐       ┌──────▼────┐
    │ • CoinDesk      │      │ Primary:     │       │ Next.js   │
    │ • Cointelegraph │      │ Google       │       │ (ISR)     │
    │ • Bitcoin Mag   │      │ Gemini       │       │           │
    │ • CryptoSlate   │      │              │       │ vivacripto│
    │ • CoinPaper     │      │ Fallback:    │       │ -frontend │
    └─────────────────┘      │ OpenAI       │       └───────────┘
                             └──────────────┘
```

## Fluxo Principal de Automação

```
1. COLETA          2. GERAÇÃO         3. VALIDAÇÃO       4. PUBLICAÇÃO
   (RSS)              (IA)              (Qualidade)         (DB)
     │                  │                   │                 │
     ▼                  ▼                   ▼                 ▼
┌─────────┐      ┌──────────────┐    ┌───────────┐    ┌───────────┐
│ News    │ ──▶  │ Content      │ ──▶│ Quality   │ ──▶│ Article   │
│Aggregator│      │ Generator    │    │ Validator │    │ Publisher │
└─────────┘      └──────────────┘    └───────────┘    └───────────┘
                        │                   │
                        ▼                   ▼
                 ┌──────────────┐    ┌───────────┐
                 │ Image        │    │ Duplicate │
                 │ Generator    │    │ Detector  │
                 └──────────────┘    └───────────┘
```

## Início Rápido

### Pré-requisitos
- Python 3.11+
- PostgreSQL 14+
- Redis (opcional, recomendado para produção)
- Chaves de API: Google Gemini, OpenAI, Cloudinary

### Setup Local
```bash
# Clonar e configurar
git clone <repo-url>
cd vivacripto-backend
cp .env.example .env

# Instalar dependências
pip install -r requirements.txt

# Configurar variáveis de ambiente no .env
# (Ver seção de configuração em stack.md)

# Executar migrations
alembic upgrade head

# Iniciar servidor
uvicorn app.main:app --reload
```

### Executar Pipeline de Automação
```bash
# Via API (requer AUTOMATION_TOKEN)
curl -X POST "http://localhost:8000/api/v1/automation/trigger" \
  -H "Authorization: Bearer $AUTOMATION_TOKEN"
```

## Contato e Suporte

Para dúvidas sobre este repositório, consulte:
1. Esta documentação em `ai_docs/`
2. O arquivo `README.md` na raiz
3. Os comentários no código (em português)

---

*Documentação gerada para otimização de contexto AI e onboarding de desenvolvedores.*

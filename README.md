# VerticeCripto Backend API

Backend FastAPI para o portal de notícias VerticeCripto.

## 🚀 Stack Técnico

- **Framework**: FastAPI (Python 3.11+)
- **Banco de Dados**: PostgreSQL 14+ + SQLAlchemy 2.0 (async)
- **Cache**: Redis
- **IA**: OpenAI (GPT-4, DALL-E 3)
- **Storage**: Cloudinary
- **Validação**: Pydantic
- **Hospedagem**: Railway/Render

## 📁 Estrutura do Projeto

```
app/
├── main.py                 # Entry point da aplicação
├── core/
│   ├── config.py           # Configurações
│   ├── security.py         # JWT e autenticação
│   └── logging.py          # Setup de logs
├── db/
│   ├── base.py             # Configuração do DB
│   └── models.py           # Modelos SQLAlchemy
├── schemas/
│   ├── post.py             # Schemas Pydantic
│   └── newsletter.py
├── crud/
│   └── crud_post.py        # Operações CRUD
├── api/
│   └── v1/
│       ├── api.py          # Router principal
│       └── endpoints/      # Endpoints da API
└── services/               # Serviços (automação, IA, etc.)
```

## 🔧 Instalação

### Requisitos

- Python 3.11+
- PostgreSQL 14+
- Redis (opcional, mas recomendado)

### Setup Local

1. Clone o repositório:
```bash
git clone https://github.com/viniciusmantegazine/verticecripto-backend.git
cd verticecripto-backend
```

2. Crie um ambiente virtual:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows
```

3. Instale as dependências:
```bash
pip install -r requirements.txt
```

4. Configure as variáveis de ambiente:
```bash
cp .env.example .env
# Edite o arquivo .env com suas credenciais
```

5. Execute as migrações do banco de dados:
```bash
alembic upgrade head
```

6. Inicie o servidor:
```bash
uvicorn app.main:app --reload
```

A API estará disponível em `http://localhost:8000`

## 📚 Documentação da API

- **Swagger UI**: http://localhost:8000/api/v1/docs
- **ReDoc**: http://localhost:8000/api/v1/redoc

## 📋 Endpoints Principais

### Posts

- `GET /api/v1/posts` - Listar posts (com paginação)
- `GET /api/v1/posts/{id}` - Obter post por ID
- `GET /api/v1/posts/slug/{slug}` - Obter post por slug
- `GET /api/v1/posts/search?q=bitcoin` - Buscar posts
- `POST /api/v1/posts` - Criar post (requer token)
- `PUT /api/v1/posts/{id}` - Atualizar post (requer token)
- `DELETE /api/v1/posts/{id}` - Deletar post (requer token)

### Newsletter

- `POST /api/v1/newsletter/subscribe` - Inscrever email

### Health

- `GET /api/v1/health` - Health check

## 🐳 Deploy

### Docker

```bash
docker build -t verticecripto-api .
docker run -p 8000:8000 --env-file .env verticecripto-api
```

### Railway/Render

1. Conecte o repositório
2. Configure as variáveis de ambiente
3. Deploy automático a cada push na branch `main`

## 🛠️ Desenvolvimento

### Criar nova migração

```bash
alembic revision --autogenerate -m "descrição da migração"
alembic upgrade head
```

### Executar testes

```bash
pytest
```

## 🔒 Segurança

- Autenticação via JWT para endpoints administrativos
- Token de serviço para automação
- CORS configurado
- Validação de entrada com Pydantic

## 📝 Variáveis de Ambiente

Veja `.env.example` para lista completa de variáveis necessárias.

## 🤝 Contribuindo

1. Crie uma branch para sua feature (`git checkout -b feature/AmazingFeature`)
2. Commit suas mudanças (`git commit -m 'Add some AmazingFeature'`)
3. Push para a branch (`git push origin feature/AmazingFeature`)
4. Abra um Pull Request

## 📄 Licença

MIT

## 📞 Suporte

Para suporte, abra uma issue no repositório GitHub.

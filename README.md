# VivaCripto Backend

Backend API para o portal de notícias de criptomoedas VivaCripto.

## 🚀 Stack Técnico

- **Runtime**: Node.js + TypeScript
- **Framework**: Express.js
- **Autenticação**: Google OAuth 2.0
- **Banco de Dados**: MySQL + Drizzle ORM
- **Validação**: Zod
- **Hospedagem**: Railway

## 📋 Pré-requisitos

- Node.js 18+
- npm ou pnpm
- MySQL 8+
- Credenciais do Google OAuth

## 🔧 Instalação

```bash
# Clonar repositório
git clone https://github.com/viniciusmantegazine/vivacripto-backend.git
cd vivacripto-backend

# Instalar dependências
npm install

# Configurar variáveis de ambiente
cp .env.example .env
# Editar .env com suas credenciais
```

## 🔐 Configuração do Google OAuth

1. Acesse [Google Cloud Console](https://console.cloud.google.com)
2. Crie um novo projeto
3. Ative a API "Google+ API"
4. Crie credenciais OAuth 2.0:
   - Tipo: Web application
   - URIs autorizados:
     - `http://localhost:3000` (desenvolvimento)
     - `https://seu-dominio.com` (produção)
   - URIs de redirecionamento autorizados:
     - `http://localhost:3000/api/auth/google/callback` (desenvolvimento)
     - `https://seu-dominio.com/api/auth/google/callback` (produção)

5. Copie `Client ID` e `Client Secret` para `.env`

## 📁 Estrutura do Projeto

```
src/
├── config/          # Configurações (env, database)
├── controllers/     # Controladores (lógica de requisição)
├── services/        # Serviços (lógica de negócio)
├── middlewares/     # Middlewares (autenticação, erro)
├── routes/          # Rotas da API
├── models/          # Modelos de dados
├── types/           # Tipos TypeScript
├── utils/           # Utilitários
└── index.ts         # Arquivo principal
```

## 🚀 Desenvolvimento

```bash
# Iniciar servidor em modo desenvolvimento
npm run dev

# Servidor rodará em http://localhost:3000
```

## 📚 API Endpoints

### Autenticação

- `GET /api/auth/google` - Obter URL de login do Google
- `POST /api/auth/google/callback` - Callback do Google OAuth
- `POST /api/auth/verify-token` - Verificar validade do token
- `POST /api/auth/logout` - Logout
- `GET /api/auth/me` - Obter usuário atual (requer autenticação)

## 🧪 Testes

```bash
# Rodar testes
npm test

# Modo watch
npm run test:watch
```

## 🗄️ Banco de Dados

```bash
# Aplicar migrações
npm run db:push

# Abrir Drizzle Studio
npm run db:studio
```

## 📦 Build e Deploy

```bash
# Build para produção
npm run build

# Iniciar em produção
npm start
```

### Deploy no Railway

1. Conectar repositório GitHub ao Railway
2. Configurar variáveis de ambiente no Railway
3. Railway fará deploy automático a cada push

## 🔒 Segurança

- Todos os tokens JWT são verificados no backend
- CORS configurado para aceitar apenas o frontend autorizado
- Variáveis sensíveis em `.env` (nunca commitar)
- Validação de entrada em todos os endpoints

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

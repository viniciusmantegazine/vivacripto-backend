-- Script de inicialização do banco de dados VivaCripto
-- Execute este script após criar o banco de dados

-- Habilitar extensões necessárias
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm"; -- Para busca de texto

-- Criar configuração de busca de texto em português
CREATE TEXT SEARCH CONFIGURATION IF NOT EXISTS pt (COPY = portuguese);

-- Inserir dados iniciais

-- Criar autor padrão
INSERT INTO authors (id, name, bio, avatar_url) 
VALUES (
    uuid_generate_v4(),
    'VivaCripto',
    'Portal de notícias sobre criptomoedas',
    NULL
) ON CONFLICT DO NOTHING;

-- Criar categorias padrão
INSERT INTO categories (id, name, slug) VALUES
    (uuid_generate_v4(), 'Bitcoin', 'bitcoin'),
    (uuid_generate_v4(), 'Ethereum', 'ethereum'),
    (uuid_generate_v4(), 'DeFi', 'defi'),
    (uuid_generate_v4(), 'NFT', 'nft'),
    (uuid_generate_v4(), 'Mercado', 'mercado'),
    (uuid_generate_v4(), 'Regulação', 'regulacao'),
    (uuid_generate_v4(), 'Tecnologia', 'tecnologia')
ON CONFLICT (slug) DO NOTHING;

-- Criar tags padrão
INSERT INTO tags (id, name, slug) VALUES
    (uuid_generate_v4(), 'Bitcoin', 'bitcoin'),
    (uuid_generate_v4(), 'Ethereum', 'ethereum'),
    (uuid_generate_v4(), 'Altcoins', 'altcoins'),
    (uuid_generate_v4(), 'DeFi', 'defi'),
    (uuid_generate_v4(), 'NFT', 'nft'),
    (uuid_generate_v4(), 'Blockchain', 'blockchain'),
    (uuid_generate_v4(), 'Trading', 'trading'),
    (uuid_generate_v4(), 'Mineração', 'mineracao'),
    (uuid_generate_v4(), 'Carteiras', 'carteiras'),
    (uuid_generate_v4(), 'Segurança', 'seguranca')
ON CONFLICT (slug) DO NOTHING;

-- Criar índices para performance
CREATE INDEX IF NOT EXISTS idx_posts_slug ON posts(slug);
CREATE INDEX IF NOT EXISTS idx_posts_published_at_desc ON posts(published_at DESC) WHERE status = 'published';
CREATE INDEX IF NOT EXISTS idx_posts_category_id ON posts(category_id);
CREATE INDEX IF NOT EXISTS idx_posts_author_id ON posts(author_id);
CREATE INDEX IF NOT EXISTS idx_posts_full_text ON posts USING GIN (to_tsvector('pt', title || ' ' || content_markdown));
CREATE INDEX IF NOT EXISTS idx_automation_logs_run_id ON automation_logs(run_id);
CREATE INDEX IF NOT EXISTS idx_automation_logs_created_at ON automation_logs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_newsletter_subscribers_email ON newsletter_subscribers(email);

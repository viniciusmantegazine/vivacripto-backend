-- Script de inicialização do banco de dados VerticeCripto
-- Execute este script após criar o banco de dados

-- Habilitar extensões necessárias
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm"; -- Para busca de texto

-- Criar configuração de busca de texto em português
-- Postgres não suporta "IF NOT EXISTS" nesse comando; usamos um bloco DO que
-- ignora o erro caso a configuração já exista (senão o script inteiro aborta
-- e o índice GIN full-text abaixo nunca é criado).
DO $$
BEGIN
    CREATE TEXT SEARCH CONFIGURATION pt (COPY = portuguese);
EXCEPTION
    WHEN duplicate_object THEN NULL;
END
$$;

-- Inserir dados iniciais

-- Criar autor padrão
-- ON CONFLICT DO NOTHING não ajuda aqui (o id é sempre novo via uuid_generate_v4
-- e não há unique em name), então re-execuções duplicavam o autor. Usamos
-- WHERE NOT EXISTS para inserir só se ainda não houver esse autor.
INSERT INTO authors (id, name, bio, avatar_url)
SELECT
    uuid_generate_v4(),
    'VerticeCripto',
    'Portal de notícias sobre criptomoedas',
    NULL
WHERE NOT EXISTS (
    SELECT 1 FROM authors WHERE name = 'VerticeCripto'
);

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

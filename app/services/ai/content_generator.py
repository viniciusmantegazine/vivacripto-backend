"""
AI Content Generator Service
Gera conteúdo de notícias usando OpenAI GPT-4
"""
from typing import Dict, Optional
from openai import AsyncOpenAI
from loguru import logger
from slugify import slugify

from app.core.config import settings


class ContentGenerator:
    """Gerador de conteúdo com IA"""
    
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = "gpt-4o-mini"  # Modelo econômico e eficiente
    
    async def generate_article(self, source_news: Dict) -> Optional[Dict]:
        """
        Gera um artigo completo a partir de uma notícia fonte
        
        Args:
            source_news: Notícia coletada das fontes
            
        Returns:
            Artigo gerado com título, conteúdo, excerpt e meta tags
        """
        try:
            title = source_news.get("title", "")
            description = source_news.get("description", "")
            source = source_news.get("source", "")
            
            logger.info(f"Gerando artigo para: {title[:50]}...")
            
            # Gerar conteúdo principal
            content = await self._generate_content(title, description, source)
            
            if not content:
                logger.warning("Falha ao gerar conteúdo")
                return None
            
            # Gerar título otimizado para SEO
            seo_title = await self._generate_seo_title(content)
            
            # Gerar excerpt
            excerpt = await self._generate_excerpt(content)
            
            # Gerar meta description
            meta_description = await self._generate_meta_description(content)
            
            # Gerar slug
            slug = slugify(seo_title or title)
            
            article = {
                "title": seo_title or title,
                "slug": slug,
                "content_markdown": content,
                "excerpt": excerpt,
                "meta_title": seo_title,
                "meta_description": meta_description,
                "source_url": source_news.get("url"),
                "source_name": source,
            }
            
            logger.info(f"Artigo gerado com sucesso: {article['title']}")
            return article
        
        except Exception as e:
            logger.error(f"Erro ao gerar artigo: {e}")
            return None
    
    async def _generate_content(
        self, 
        title: str, 
        description: str,
        source: str
    ) -> Optional[str]:
        """Gera o conteúdo principal do artigo"""
        prompt = f"""Você é um jornalista especializado em criptomoedas escrevendo para o portal VivaCripto (vivacripto.com.br).

Notícia original:
Título: {title}
Descrição: {description}
Fonte: {source}

INSTRUÇÕES:
1. Reescreva a notícia em português brasileiro com 150-200 palavras
2. Use linguagem jornalística simples e objetiva
3. Adicione contexto e análise leve quando relevante
4. NÃO faça recomendações financeiras ou calls de trade
5. NÃO traduza literalmente - reescreva com ângulo próprio
6. Foque em informar, não em opinar
7. Use markdown para formatação (negrito, itálico, listas)
8. Estruture em 2-3 parágrafos curtos

IMPORTANTE: Este é conteúdo informativo gerado por IA. Não inclua avisos sobre isso no texto.

Escreva o artigo:"""

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "Você é um jornalista especializado em criptomoedas."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=500,
            )
            
            content = response.choices[0].message.content.strip()
            return content
        
        except Exception as e:
            logger.error(f"Erro ao gerar conteúdo: {e}")
            return None
    
    async def _generate_seo_title(self, content: str) -> Optional[str]:
        """Gera título otimizado para SEO (50-60 caracteres)"""
        prompt = f"""Com base no conteúdo abaixo, crie um título otimizado para SEO:

Conteúdo:
{content[:500]}

REQUISITOS:
- 50-60 caracteres
- Inclua palavra-chave principal
- Seja atrativo mas não clickbait
- Em português brasileiro

Título:"""

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.5,
                max_tokens=50,
            )
            
            title = response.choices[0].message.content.strip()
            # Remover aspas se houver
            title = title.strip('"\'')
            return title
        
        except Exception as e:
            logger.error(f"Erro ao gerar título SEO: {e}")
            return None
    
    async def _generate_excerpt(self, content: str) -> Optional[str]:
        """Gera excerpt do artigo (100-120 caracteres)"""
        # Pegar primeiras 2 frases do conteúdo
        sentences = content.split('. ')[:2]
        excerpt = '. '.join(sentences)
        
        # Limitar a 120 caracteres
        if len(excerpt) > 120:
            excerpt = excerpt[:117] + "..."
        
        return excerpt
    
    async def _generate_meta_description(self, content: str) -> Optional[str]:
        """Gera meta description para SEO (150-160 caracteres)"""
        prompt = f"""Com base no conteúdo abaixo, crie uma meta description para SEO:

Conteúdo:
{content[:500]}

REQUISITOS:
- 150-160 caracteres
- Inclua palavra-chave principal
- Seja descritivo e atrativo
- Em português brasileiro

Meta description:"""

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.5,
                max_tokens=60,
            )
            
            meta_desc = response.choices[0].message.content.strip()
            # Remover aspas se houver
            meta_desc = meta_desc.strip('"\'')
            return meta_desc
        
        except Exception as e:
            logger.error(f"Erro ao gerar meta description: {e}")
            return None

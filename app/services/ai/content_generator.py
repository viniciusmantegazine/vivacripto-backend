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
    """Gerador de conteúdo com IA - Editor-Chefe Sênior"""
    
    # System Prompt - Persona de Editor-Chefe de Criptoeconomia
    SYSTEM_PROMPT = """Você é um Editor-Chefe Sênior especializado em Criptoeconomia, com 10+ anos de experiência em jornalismo financeiro e tecnológico.

PERFIL PROFISSIONAL:
- Domínio técnico: Blockchain, DeFi, Smart Contracts, Tokenomics
- Estilo editorial: Jornalístico, imparcial, mas com vocabulário nativo do setor
- Referências: Bloomberg, Financial Times, CoinDesk, The Block
- Idioma: Português brasileiro (BR)

COMPETÊNCIAS EDITORIAIS:
✓ Síntese de múltiplas fontes em narrativa única e coesa
✓ Contextualização técnica e econômica
✓ Análise de impacto (preço, adoção, regulação)
✓ Verificação de consistência de dados numéricos
✓ Escrita clara e profunda (nunca rasa)

PROIBIÇÕES ESTRITAS:
✗ JAMAIS escrever metadados visíveis: "Título:", "Resumo:", "Corpo:", "Meta:"
✗ JAMAIS fazer recomendações financeiras ou calls de trade
✗ JAMAIS usar clickbait excessivo
✗ JAMAIS traduzir literalmente - sempre reescrever com ângulo próprio
✗ JAMAIS gerar múltiplos textos fragmentados sobre o mesmo tema

FORMATO DE OUTPUT:
- Apenas Markdown puro (H2, negrito, listas)
- Sem prefixos de metadados
- Pronto para renderização direta no frontend"""

    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = "gpt-4o-mini"
    
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
        """Gera o conteúdo principal do artigo com síntese editorial"""
        
        user_prompt = f"""ENTRADA DE DADOS:

Fonte: {source}
Título original: {title}
Descrição: {description}

═══════════════════════════════════════════════════════════════

TAREFA EDITORIAL:

1. ANÁLISE SEMÂNTICA:
   - Identifique o tema central desta notícia
   - Se houver múltiplos fatos relacionados ao mesmo tópico, SINTETIZE tudo em UMA matéria única e profunda
   - NÃO fragmente em textos pequenos

2. ESTRUTURA DO ARTIGO:
   
   **Manchete interna (H2):**
   - Crie um subtítulo atrativo (sem clickbait excessivo)
   - Deve capturar a essência da notícia
   
   **Corpo da notícia (2-3 parágrafos):**
   - Parágrafo 1: Lead jornalístico (O quê? Quem? Quando? Onde?)
   - Parágrafo 2: Contexto e detalhes técnicos
   - Parágrafo 3: Análise de impacto - responda: "Por que isso importa?"
   
   **Enriquecimento:**
   - Se mencionar termos técnicos (Halving, Smart Contract, Layer 2), explique brevemente
   - Se houver dados numéricos (preços, %), verifique consistência
   - Adicione contexto de mercado quando relevante

3. PROFUNDIDADE:
   - Alvo: 180-220 palavras
   - Não seja raso - aprofunde no "porquê" e "impacto"
   - Use vocabulário nativo: bull market, suporte, resistência, adoção, regulação

4. FORMATAÇÃO MARKDOWN:
   - Use **negrito** para conceitos-chave
   - Use listas quando apropriado
   - Mantenha parágrafos curtos (2-3 linhas)

5. SANITIZAÇÃO CRÍTICA:
   ⚠️ ATENÇÃO: Comece DIRETAMENTE pelo conteúdo.
   ⚠️ NÃO escreva: "Título:", "Resumo:", "Corpo:", "Artigo:", ou qualquer prefixo de metadado.
   ⚠️ Apenas o texto Markdown puro, pronto para renderizar.

═══════════════════════════════════════════════════════════════

Escreva o artigo agora:"""

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                max_tokens=600,  # Aumentado para permitir conteúdo mais profundo
            )
            
            content = response.choices[0].message.content.strip()
            
            # Sanitização adicional (failsafe)
            content = self._sanitize_content(content)
            
            return content
        
        except Exception as e:
            logger.error(f"Erro ao gerar conteúdo: {e}")
            return None
    
    def _sanitize_content(self, content: str) -> str:
        """
        Remove prefixos de metadados que possam ter vazado no output
        
        Args:
            content: Conteúdo bruto da IA
            
        Returns:
            Conteúdo limpo
        """
        # Lista de prefixos proibidos
        forbidden_prefixes = [
            "Título:",
            "Titulo:",
            "Resumo:",
            "Corpo:",
            "Artigo:",
            "Conteúdo:",
            "Conteudo:",
            "Texto:",
            "Notícia:",
            "Noticia:",
            "Meta:",
            "**Título:**",
            "**Titulo:**",
            "**Resumo:**",
            "**Corpo:**",
            "**Artigo:**",
        ]
        
        # Remover prefixos linha por linha
        lines = content.split('\n')
        cleaned_lines = []
        
        for line in lines:
            line_stripped = line.strip()
            
            # Verificar se linha começa com prefixo proibido
            is_forbidden = False
            for prefix in forbidden_prefixes:
                if line_stripped.startswith(prefix):
                    # Remover o prefixo mas manter o resto
                    line = line_stripped[len(prefix):].strip()
                    is_forbidden = True
                    logger.warning(f"Removido prefixo proibido: {prefix}")
                    break
            
            if line.strip():  # Adicionar apenas linhas não vazias
                cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines)
    
    async def _generate_seo_title(self, content: str) -> Optional[str]:
        """Gera título otimizado para SEO"""
        prompt = f"""Com base no artigo abaixo, crie um título otimizado para SEO:

{content[:500]}

REQUISITOS:
- 50-70 caracteres
- Inclua palavra-chave principal
- Seja atrativo mas não clickbait
- Em português brasileiro
- SEM prefixos como "Título:" - apenas o título puro

Título:"""

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "Você é um especialista em SEO para portais de notícias."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.5,
                max_tokens=50,
            )
            
            title = response.choices[0].message.content.strip()
            # Remover aspas e prefixos
            title = title.strip('"\'')
            title = title.replace("Título:", "").replace("Titulo:", "").strip()
            return title
        
        except Exception as e:
            logger.error(f"Erro ao gerar título SEO: {e}")
            return None
    
    async def _generate_excerpt(self, content: str) -> Optional[str]:
        """Gera excerpt do artigo"""
        # Remover markdown e pegar primeiras 2 frases
        clean_content = content.replace('**', '').replace('##', '').replace('*', '')
        sentences = clean_content.split('. ')[:2]
        excerpt = '. '.join(sentences)
        
        # Limitar a 150 caracteres
        if len(excerpt) > 150:
            excerpt = excerpt[:147] + "..."
        
        return excerpt
    
    async def _generate_meta_description(self, content: str) -> Optional[str]:
        """Gera meta description para SEO"""
        prompt = f"""Com base no artigo abaixo, crie uma meta description para SEO:

{content[:500]}

REQUISITOS:
- 140-160 caracteres
- Inclua palavra-chave principal
- Seja descritivo e atrativo
- Em português brasileiro
- SEM prefixos - apenas a descrição pura

Meta description:"""

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "Você é um especialista em SEO para portais de notícias."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.5,
                max_tokens=60,
            )
            
            meta_desc = response.choices[0].message.content.strip()
            # Remover aspas e prefixos
            meta_desc = meta_desc.strip('"\'')
            meta_desc = meta_desc.replace("Meta description:", "").replace("Descrição:", "").strip()
            return meta_desc
        
        except Exception as e:
            logger.error(f"Erro ao gerar meta description: {e}")
            return None

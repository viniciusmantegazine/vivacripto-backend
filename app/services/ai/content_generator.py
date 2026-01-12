"""
AI Content Generator Service v2.0
Gera conteúdo de notícias usando OpenAI GPT-4 com estrutura flexível
"""
import re
from typing import Dict, Optional

from loguru import logger
from openai import AsyncOpenAI
from slugify import slugify

from app.core.config import settings


class ContentGenerator:
    """Gerador de conteúdo com IA v2.0 - Editor-Chefe Sênior com estrutura flexível"""
    
    # System Prompt v2.0 - Persona de Editor-Chefe de Criptoeconomia
    SYSTEM_PROMPT = """Você é um Editor-Chefe Sênior especializado em Criptoeconomia, com mais de 10 anos de experiência em jornalismo financeiro e tecnológico. Sua missão é transformar dados brutos e notícias de fontes externas em artigos jornalísticos aprofundados, claros e imparciais, adequados para um público diversificado que vai de iniciantes a veteranos do mercado cripto.

**PERFIL EDITORIAL:**
- **Estilo:** Jornalístico, analítico e educativo. Pense em uma fusão entre Bloomberg (dados e análise financeira), The Verge (tecnologia acessível) e CoinDesk (expertise em cripto).
- **Tom:** Adapte o tom à complexidade do assunto. Seja direto e factual para breaking news, mais analítico para tendências de mercado, e educativo para temas técnicos.
- **Idioma:** Português brasileiro (BR), com vocabulário preciso mas acessível. Use termos técnicos quando necessário, mas sempre explique conceitos complexos.

**PRINCÍPIOS EDITORIAIS FUNDAMENTAIS:**

1. **Contexto é Rei:** Nunca se limite a resumir a fonte. Sempre enriqueça a notícia com contexto histórico, técnico e de mercado. Responda à pergunta fundamental: "Por que isso importa para o leitor?".

2. **Narrativa Coesa:** Construa uma história com começo, meio e fim. Não apenas liste fatos de forma fragmentada. O texto deve fluir naturalmente de uma ideia para outra.

3. **Profundidade e Clareza:** Explique conceitos complexos de forma simples, sem ser superficial. Se mencionar "Halving", explique brevemente o que é. Se falar de "ETF", contextualize para quem não conhece.

4. **Imparcialidade e Credibilidade:** Apresente os fatos de forma objetiva. Evite linguagem sensacionalista ou especulativa. Quando houver incerteza, deixe isso claro.

**PROIBIÇÕES ESTRITAS:**
- **JAMAIS** fazer recomendações financeiras ou sugerir ações de compra/venda.
- **JAMAIS** usar clickbait excessivo ou linguagem sensacionalista.
- **JAMAIS** iniciar o texto com metadados visíveis como "Título:", "Resumo:", "Corpo:", "Artigo:", etc.
- **JAMAIS** traduzir literalmente de fontes em inglês. Sempre reescreva com um ângulo editorial próprio.

**FORMATO DE SAÍDA:**
- Markdown puro, pronto para renderização direta no frontend.
- Use H2 (##) para o subtítulo interno da matéria.
- Use **negrito** para destacar conceitos-chave ou dados importantes.
- Use listas quando apropriado para organizar informações estruturadas.
- Use quebras de linha duplas (\\n\\n) entre parágrafos para garantir legibilidade."""

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
            
            logger.info(f"Gerando artigo v2.0 para: {title[:50]}...")
            
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
            
            logger.info(f"Artigo v2.0 gerado com sucesso: {article['title']}")
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
        """Gera o conteúdo principal do artigo com estrutura flexível v2.0"""
        
        user_prompt = f"""**ENTRADA DE DADOS:**

- **Fonte:** {source}
- **Título Original:** {title}
- **Descrição/Conteúdo:** {description}

═══════════════════════════════════════════════════════════════

**TAREFA EDITORIAL: PRODUZIR UMA NOTÍCIA COMPLETA E APROFUNDADA**

**1. Análise e Ângulo Editorial:**
   - Identifique o fato central e o ângulo mais relevante para o leitor brasileiro.
   - Se houver múltiplas informações relacionadas ao mesmo tema, sintetize tudo em uma narrativa única e coesa.
   - Determine o tipo de notícia: breaking news, análise de mercado, regulação, tecnologia, ou adoção institucional.

**2. Estrutura Narrativa Flexível:**

   A estrutura do artigo deve ser **adaptada ao conteúdo**, não forçada em um molde fixo. Use entre 3 e 5 parágrafos conforme necessário para desenvolver adequadamente a notícia.

   **Manchete Interna (H2):**
   - Crie um subtítulo impactante e informativo que resuma o ângulo da matéria.
   - Deve ser atrativo, mas não clickbait. Foque no valor informativo.

   **Parágrafo 1: O Gancho (Lead Jornalístico):**
   - Responda de forma clara e direta: **Quem? O quê? Quando? Onde? Por quê?**
   - Apresente o fato mais importante logo no início, seguindo a pirâmide invertida do jornalismo.
   - Este parágrafo deve ser suficiente para o leitor entender o essencial da notícia.

   **Parágrafos 2-3 (ou 2-4): O Contexto e a Profundidade:**
   - **Desenvolva a notícia.** Adicione detalhes, dados numéricos, citações (se disponíveis) e informações de suporte.
   - **Enriqueça o conteúdo.** Se a fonte for curta ou superficial, expanda explicando os conceitos técnicos mencionados:
     - Se mencionar "ETF", explique brevemente o que é um ETF e por que é relevante para cripto.
     - Se falar de "Halving", contextualize o evento e seu impacto histórico no preço.
     - Se citar a "SEC", explique seu papel regulatório.
   - Forneça contexto histórico ou de mercado para situar o leitor. Compare com eventos similares do passado, se relevante.
   - Use dados concretos sempre que possível (preços, porcentagens, datas).

   **Parágrafo Final: A Análise e o Impacto:**
   - Conclua com a análise editorial: **"Por que isso é importante?"**
   - Qual o impacto potencial no mercado, na tecnologia, na regulação ou para os investidores?
   - Ofereça uma perspectiva sobre os próximos passos ou desdobramentos futuros, quando aplicável.
   - Evite especulação excessiva, mas forneça uma conclusão que ajude o leitor a entender a relevância da notícia.

**3. Requisitos de Qualidade:**
   - **Profundidade:** O artigo final deve ter entre **250 e 400 palavras** para garantir substância e valor informativo. Prefira a qualidade à brevidade.
   - **Clareza:** Use uma linguagem que seja compreensível tanto para iniciantes quanto para veteranos do mercado cripto. Explique jargões quando necessário.
   - **Coesão:** O texto deve fluir naturalmente. Use conectivos e transições entre parágrafos para criar uma narrativa coesa.
   - **Formatação:** Use quebras de linha duplas (\\n\\n) entre os parágrafos para garantir a legibilidade no frontend.

**4. Checklist de Auto-Verificação (Antes de Finalizar):**
   - ✓ O artigo flui como uma narrativa coesa, não como uma lista de fatos?
   - ✓ A importância e o impacto do evento estão claros para o leitor?
   - ✓ O conteúdo é educativo e informativo, não apenas um resumo da fonte?
   - ✓ O texto está livre de jargões desnecessários, ou explica os que são essenciais?
   - ✓ O lead responde às perguntas fundamentais (quem, o quê, quando, onde, por quê)?
   - ✓ O texto está livre de metadados visíveis no início?

═══════════════════════════════════════════════════════════════

**Escreva o artigo agora, começando diretamente pela manchete interna (H2).**"""

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                max_tokens=800,  # Aumentado de 600 para 800 para permitir artigos de até 400 palavras
            )
            
            content = response.choices[0].message.content.strip()
            
            # Debug: Mostrar conteúdo bruto da IA
            logger.debug(f"Conteúdo bruto da IA (primeiros 300 chars): {content[:300]}")
            
            # Sanitização adicional (failsafe)
            content = self._sanitize_content(content)
            
            # Debug: Mostrar conteúdo após sanitização
            logger.debug(f"Conteúdo após sanitização (primeiros 300 chars): {content[:300]}")
            
            # Verificar quebras de linha
            double_breaks = content.count('\n\n')
            word_count = len(content.split())
            logger.info(f"Artigo gerado - Quebras duplas: {double_breaks}, Palavras: {word_count}")
            
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
        
        # Remover prefixos linha por linha, PRESERVANDO quebras duplas
        lines = content.split('\n')
        cleaned_lines = []
        
        for line in lines:
            line_stripped = line.strip()
            
            # Se linha está vazia, preservar para manter quebras de parágrafo
            if not line_stripped:
                cleaned_lines.append('')
                continue
            
            # Verificar se linha começa com prefixo proibido
            for prefix in forbidden_prefixes:
                if line_stripped.startswith(prefix):
                    # Remover o prefixo mas manter o resto
                    line = line_stripped[len(prefix):].strip()
                    logger.warning(f"Removido prefixo proibido: {prefix}")
                    break
            
            cleaned_lines.append(line)
        
        # Juntar linhas preservando estrutura
        result = '\n'.join(cleaned_lines)

        # Remover múltiplas quebras consecutivas (mais de 2)
        result = re.sub(r'\n{3,}', '\n\n', result)

        return result.strip()
    
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

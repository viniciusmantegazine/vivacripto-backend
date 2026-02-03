"""
Weekly Report Generator Service v1.0
Gera relatórios semanais de análise macro + Bitcoin usando Claude Opus

Este serviço é diferente do ContentGenerator padrão:
- Usa Claude Opus para análises profundas (vs. Gemini Flash para notícias)
- Prompts muito mais extensos e estruturados
- Gera conteúdo analítico longo (1500-3000 palavras vs. 250-500)
- Usado esporadicamente (semanal vs. diário)
"""
from datetime import datetime
from typing import Dict, Optional

from loguru import logger
from slugify import slugify

from app.core.config import settings
from app.services.ai.prompts.weekly_report_prompts import (
    WEEKLY_REPORT_SYSTEM_PROMPT,
    WEEKLY_REPORT_IMAGE_PROMPT,
)

# Anthropic Claude imports
try:
    from anthropic import AsyncAnthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    logger.warning("Anthropic SDK não instalado. Relatórios semanais não disponíveis.")


class WeeklyReportGenerator:
    """
    Gerador de Relatórios Semanais v1.0 - Claude Opus

    Gera relatórios analíticos profundos sobre o mercado de criptomoedas
    com foco em Bitcoin e cenário macroeconômico dos EUA.

    Diferenças do ContentGenerator:
    - Modelo: Claude Opus (vs. Gemini Flash)
    - Tamanho: 1500-3000 palavras (vs. 250-500)
    - Frequência: Semanal (vs. Diário)
    - Prompt: Fixo e extenso (vs. Dinâmico por notícia)
    """

    # Modelos Claude
    CLAUDE_MODEL = "claude-opus-4-20250514"
    CLAUDE_FALLBACK_MODEL = "claude-sonnet-4-20250514"

    # Configurações de geração
    MAX_TOKENS = 8192  # Relatórios longos precisam de mais tokens
    TEMPERATURE = 0.7  # Um pouco mais criativo para análises

    def __init__(self):
        """Inicializa o gerador de relatórios semanais"""
        self.claude_client = None
        self.claude_available = False

        self._init_claude_client()

        # Import lazy do ImageGenerator para evitar circular imports
        self._image_generator = None

    def _init_claude_client(self):
        """Inicializa o cliente Anthropic/Claude"""
        if not ANTHROPIC_AVAILABLE:
            logger.warning("WeeklyReportGenerator: Anthropic SDK não disponível")
            return

        if not settings.ANTHROPIC_API_KEY:
            logger.warning("WeeklyReportGenerator: ANTHROPIC_API_KEY não configurada")
            return

        try:
            self.claude_client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
            self.claude_available = True
            logger.info(f"WeeklyReportGenerator v1.0: Claude configurado ({self.CLAUDE_MODEL})")
        except Exception as e:
            logger.error(f"Falha ao inicializar Claude: {e}")

    @property
    def image_generator(self):
        """Lazy load do ImageGenerator"""
        if self._image_generator is None:
            from app.services.ai.image_generator import ImageGenerator
            self._image_generator = ImageGenerator()
        return self._image_generator

    async def generate_report(self) -> Optional[Dict]:
        """
        Gera um relatório semanal completo de análise macro + Bitcoin

        Returns:
            Dict com:
                - title: Título do relatório
                - slug: Slug para URL
                - content_markdown: Conteúdo em Markdown
                - excerpt: Resumo curto
                - meta_title: Título SEO
                - meta_description: Descrição SEO
                - image_url: URL da imagem (se gerada)
                - word_count: Contagem de palavras
                - category: "analise-semanal"
        """
        if not self.claude_available:
            logger.error("Claude não disponível. Configure ANTHROPIC_API_KEY.")
            return None

        try:
            logger.info("Iniciando geração de relatório semanal...")

            # 1. Gerar conteúdo com Claude
            content = await self._generate_content()

            if not content:
                logger.error("Falha ao gerar conteúdo do relatório")
                return None

            # 2. Gerar título
            title = await self._generate_title(content)

            # 3. Gerar excerpt
            excerpt = self._generate_excerpt(content)

            # 4. Gerar meta description
            meta_description = self._generate_meta_description(content, title)

            # 5. Gerar slug
            slug = slugify(title)

            # 6. Gerar imagem
            image_url = await self._generate_image(title, content)

            # 7. Calcular word count
            word_count = len(content.split())

            report = {
                "title": title,
                "slug": slug,
                "content_markdown": content,
                "excerpt": excerpt,
                "meta_title": title[:70] if len(title) > 70 else title,
                "meta_description": meta_description,
                "image_url": image_url,
                "word_count": word_count,
                "category": "analise-semanal",
                "generated_at": datetime.utcnow().isoformat(),
            }

            logger.info(f"Relatório semanal gerado: {title} ({word_count} palavras)")
            return report

        except Exception as e:
            logger.error(f"Erro ao gerar relatório semanal: {e}")
            return None

    async def _generate_content(self) -> Optional[str]:
        """Gera o conteúdo principal do relatório usando Claude Opus"""

        # User prompt solicita a geração do relatório
        user_prompt = f"""Gere um relatório semanal completo de análise do mercado de criptomoedas,
seguindo RIGOROSAMENTE a estrutura definida no system prompt.

Data de referência: {datetime.utcnow().strftime("%d/%m/%Y")}

IMPORTANTE:
1. Siga a estrutura de 7 partes obrigatória
2. Use dados públicos e bem conhecidos do mercado
3. Mantenha tom analítico e profissional
4. Inclua o disclaimer de não ser aconselhamento financeiro
5. Mínimo 1500 palavras, máximo 3000 palavras
6. Formate em Markdown com ## para seções principais e ### para subseções

Gere o relatório completo agora:"""

        content = None

        # Tentar Claude Opus primeiro
        try:
            logger.info(f"[Claude] Gerando relatório com {self.CLAUDE_MODEL}...")

            response = await self.claude_client.messages.create(
                model=self.CLAUDE_MODEL,
                max_tokens=self.MAX_TOKENS,
                temperature=self.TEMPERATURE,
                system=WEEKLY_REPORT_SYSTEM_PROMPT,
                messages=[
                    {"role": "user", "content": user_prompt}
                ]
            )

            content = response.content[0].text.strip()
            logger.info(f"[Claude] Relatório gerado com sucesso ({len(content)} chars)")

        except Exception as e:
            logger.warning(f"[Claude Opus] Falha: {e}. Tentando fallback...")

            # Tentar fallback com Sonnet
            try:
                logger.info(f"[Claude] Tentando fallback com {self.CLAUDE_FALLBACK_MODEL}...")

                response = await self.claude_client.messages.create(
                    model=self.CLAUDE_FALLBACK_MODEL,
                    max_tokens=self.MAX_TOKENS,
                    temperature=self.TEMPERATURE,
                    system=WEEKLY_REPORT_SYSTEM_PROMPT,
                    messages=[
                        {"role": "user", "content": user_prompt}
                    ]
                )

                content = response.content[0].text.strip()
                logger.info(f"[Claude Fallback] Relatório gerado com sucesso ({len(content)} chars)")

            except Exception as e2:
                logger.error(f"[Claude] Falha total na geração: {e2}")
                return None

        return content

    async def _generate_title(self, content: str) -> str:
        """Gera um título para o relatório baseado no conteúdo"""

        # Extrair data atual para o título
        today = datetime.utcnow()
        week_str = today.strftime("%d/%m/%Y")

        # Prompt para gerar título
        title_prompt = f"""Com base no relatório de análise semanal abaixo, gere um título
curto e impactante (máximo 80 caracteres) que capture a essência da semana.

O título deve:
- Ser informativo e profissional
- Mencionar Bitcoin ou mercado cripto
- Refletir o tom geral da análise (otimista, pessimista ou neutro)
- NÃO incluir a data (será adicionada separadamente)

Conteúdo do relatório (primeiros 500 caracteres):
{content[:500]}...

Responda APENAS com o título, sem aspas ou explicações:"""

        try:
            response = await self.claude_client.messages.create(
                model=self.CLAUDE_FALLBACK_MODEL,  # Usar modelo mais rápido para título
                max_tokens=100,
                temperature=0.5,
                messages=[
                    {"role": "user", "content": title_prompt}
                ]
            )

            title = response.content[0].text.strip()
            # Limitar tamanho e limpar
            title = title.replace('"', '').replace("'", "")[:80]

            return title

        except Exception as e:
            logger.warning(f"Falha ao gerar título: {e}. Usando título padrão.")
            return f"Análise Semanal Bitcoin - {week_str}"

    def _generate_excerpt(self, content: str) -> str:
        """Gera um excerpt do relatório (primeiras 2-3 frases)"""

        # Pegar as primeiras linhas que não são cabeçalhos
        lines = content.split("\n")
        excerpt_parts = []

        for line in lines:
            line = line.strip()
            # Pular linhas vazias e cabeçalhos
            if not line or line.startswith("#") or line.startswith("═"):
                continue
            # Pegar apenas texto normal
            excerpt_parts.append(line)
            if len(" ".join(excerpt_parts)) > 200:
                break

        excerpt = " ".join(excerpt_parts)

        # Truncar em 300 caracteres
        if len(excerpt) > 300:
            excerpt = excerpt[:297] + "..."

        return excerpt or "Análise semanal completa do mercado de criptomoedas com foco em Bitcoin e cenário macroeconômico."

    def _generate_meta_description(self, content: str, title: str) -> str:
        """Gera uma meta description SEO-friendly"""

        # Usar título + parte do excerpt
        base = f"{title}. "
        remaining = 160 - len(base)

        if remaining > 50:
            excerpt = self._generate_excerpt(content)
            # Pegar início do excerpt
            meta = base + excerpt[:remaining - 3] + "..."
        else:
            meta = title[:157] + "..."

        return meta[:160]

    async def _generate_image(self, title: str, content: str) -> Optional[str]:
        """Gera imagem de capa para o relatório com estilo específico"""

        try:
            logger.info("Gerando imagem para relatório semanal...")

            # Usar o prompt específico para relatórios
            image_url = await self.image_generator.generate_and_upload_image(
                title=title,
                content=WEEKLY_REPORT_IMAGE_PROMPT,  # Usar prompt fixo de relatório
                category_name="analise-semanal",
                use_contextual_analysis=False  # Usar prompt direto, não análise contextual
            )

            if image_url:
                logger.info(f"Imagem do relatório gerada: {image_url[:50]}...")
            else:
                logger.warning("Falha ao gerar imagem do relatório")

            return image_url

        except Exception as e:
            logger.error(f"Erro ao gerar imagem do relatório: {e}")
            return None


# Instância singleton para uso no projeto
weekly_report_generator = WeeklyReportGenerator()

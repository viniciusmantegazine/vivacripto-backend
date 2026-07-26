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

    # Modelos Claude. IDs sem sufixo de data — não acrescentar um.
    # Os anteriores (claude-opus-4-20250514 / claude-sonnet-4-20250514) foram
    # depreciados com retirada em 15/jun/2026; primário e fallback eram da
    # mesma geração, então o fallback não salvava nada.
    CLAUDE_MODEL = "claude-opus-5"
    CLAUDE_FALLBACK_MODEL = "claude-sonnet-5"

    # Configurações de geração.
    # 16000 e não 8192: nos modelos atuais o thinking vem ligado por padrão e
    # divide este teto com o texto da resposta. Um relatório de 3000 palavras
    # em português já consome ~4500 tokens sozinho.
    # NÃO reintroduzir `temperature`/`top_p`/`top_k`: foram removidos da API
    # nos modelos atuais e causam HTTP 400. O tom vive no system prompt.
    MAX_TOKENS = 16000

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

    async def generate_report(self, generate_image: bool = True) -> Optional[Dict]:
        """
        Gera um relatório semanal completo de análise macro + Bitcoin

        Args:
            generate_image: Se False, pula a geração de imagem (usado no preview,
                            onde a imagem seria descartada — evita custo à toa).

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

            # 6. Gerar imagem (pulada no preview para não gastar sem necessidade)
            image_url = None
            if generate_image:
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

    async def _call_claude(self, model: str, user_prompt: str) -> Optional[str]:
        """
        Faz UMA chamada ao Claude e devolve o texto do relatório.

        Existe para desduplicar: o primário e o fallback tinham blocos de
        chamada idênticos, então cada correção precisava ser aplicada duas
        vezes — foi assim que os defeitos de parâmetro e de leitura da
        resposta sobreviveram.

        Usa streaming porque relatório longo + thinking é o caso clássico de
        requisição não-streaming estourar timeout de HTTP. `get_final_message`
        devolve a resposta completa, então quem chama não lida com eventos.

        Devolve None quando não há texto utilizável (sem levantar exceção).
        """
        async with self.claude_client.messages.stream(
            model=model,
            max_tokens=self.MAX_TOKENS,
            system=WEEKLY_REPORT_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        ) as stream:
            message = await stream.get_final_message()

        # Recusa por classificador vem como HTTP 200, não como exceção: o
        # try/except de quem chama não pega. Qualquer texto presente é
        # parcial e não deve ser publicado.
        if getattr(message, "stop_reason", None) == "refusal":
            logger.error(
                f"[Claude] {model} recusou a geração (classificador de segurança)"
            )
            return None

        text = self._extract_text(message)
        if not text:
            logger.error(f"[Claude] {model} não retornou bloco de texto")
            return None
        return text

    def _extract_text(self, message) -> Optional[str]:
        """
        Extrai o texto da resposta do Claude.

        NÃO usar `message.content[0].text`: nos modelos atuais o thinking vem
        ligado por padrão e seus blocos vêm ANTES do texto, então o primeiro
        bloco não tem `.text` e o acesso direto estoura AttributeError.
        Varremos os blocos e pegamos o primeiro de tipo "text".
        """
        for block in message.content:
            if getattr(block, "type", None) == "text":
                return block.text.strip()
        return None

    async def _generate_content(self) -> Optional[str]:
        """Gera o conteúdo principal do relatório usando Claude Opus"""

        # Coletar dados de mercado em tempo real
        from app.services.ai.market_data_collector import market_data_collector

        logger.info("Coletando dados de mercado em tempo real...")
        market_data = await market_data_collector.collect_all()
        logger.info(f"Dados de mercado coletados: {len(market_data)} caracteres")

        # User prompt com dados reais injetados
        user_prompt = f"""Gere um relatório semanal completo de análise do mercado de criptomoedas,
seguindo RIGOROSAMENTE a estrutura definida no system prompt.

Data de referência: {datetime.utcnow().strftime("%d/%m/%Y")}

{market_data}

REGRAS DE FORMATAÇÃO OBRIGATÓRIAS:
1. NÃO inclua título principal - comece direto com "## Cenário Macroeconômico dos EUA"
2. NÃO use emojis em nenhum lugar do texto
3. Use ## para seções principais (ex: ## Cenário Macroeconômico dos EUA)
4. Use ### para subseções numeradas (ex: ### 1.1 Política Monetária)
5. Use **negrito** para valores numéricos e termos importantes
6. Use listas com hífen (-) para itens
7. Separe seções com --- (linha horizontal)
8. Mínimo 1500 palavras, máximo 3000 palavras
9. Inclua disclaimer de não ser aconselhamento financeiro no final
10. Use os DADOS DE MERCADO fornecidos acima como fonte primária para preços e indicadores
11. Mantenha tom analítico e profissional

Gere o relatório completo agora:"""

        # Primário; em falha ou resposta sem texto, tenta o fallback.
        try:
            logger.info(f"[Claude] Gerando relatório com {self.CLAUDE_MODEL}...")
            content = await self._call_claude(self.CLAUDE_MODEL, user_prompt)
            if content:
                logger.info(f"[Claude] Relatório gerado com sucesso ({len(content)} chars)")
                return content
            logger.warning("[Claude] Primário não produziu texto. Tentando fallback...")
        except Exception as e:
            logger.warning(f"[Claude] Falha no primário: {e}. Tentando fallback...")

        try:
            logger.info(f"[Claude] Tentando fallback com {self.CLAUDE_FALLBACK_MODEL}...")
            content = await self._call_claude(self.CLAUDE_FALLBACK_MODEL, user_prompt)
            if content:
                logger.info(f"[Claude Fallback] Relatório gerado com sucesso ({len(content)} chars)")
                return content
            logger.error("[Claude] Fallback também não produziu texto")
            return None
        except Exception as e2:
            logger.error(f"[Claude] Falha total na geração: {e2}")
            return None

    async def _generate_title(self, content: str) -> str:
        """Retorna o título do relatório semanal com número da semana atual"""
        week_number = datetime.utcnow().isocalendar()[1]
        return f"Giro semanal do mercado cripto semana {week_number:02d}"

    def _generate_excerpt(self, content: str) -> str:
        """Gera um excerpt do relatório (primeiras 2-3 frases)"""

        # Pegar as primeiras linhas que não são cabeçalhos ou listas
        lines = content.split("\n")
        excerpt_parts = []

        for line in lines:
            line = line.strip()
            # Pular linhas vazias, cabeçalhos, separadores e listas
            if not line or line.startswith("#") or line.startswith("═") or line.startswith("-") or line.startswith("---"):
                continue
            # Pular linhas que começam com "Analise:" ou "Liste:"
            if line.startswith("Analise:") or line.startswith("Liste:"):
                continue
            # Pegar apenas texto normal (parágrafos)
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

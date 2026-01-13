"""
Image Generation Service - Data Visualization Style v6.0
Gera visualizações de dados abstratas e sofisticadas com estética de terminal financeiro
Inclui sanitização de temas para evitar imagens inadequadas
"""
import asyncio
import re
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

from openai import AsyncOpenAI
import cloudinary
import cloudinary.uploader

from app.core.config import settings
from app.core.logging import logger

# ThreadPool para operações síncronas do Cloudinary
_cloudinary_executor = ThreadPoolExecutor(max_workers=3)

# Mapeamento de categorias para temas visuais abstratos (sem conteúdo literal)
CATEGORY_VISUAL_THEMES = {
    "bitcoin": "golden digital currency network with ascending trend lines",
    "ethereum": "purple hexagonal smart contract ecosystem with interconnected nodes",
    "altcoins": "multicolored constellation of digital assets and market flows",
    "defi": "decentralized finance protocol layers with liquidity pools visualization",
    "regulacao": "structured compliance framework with institutional data streams",
    "airdrop": "particle distribution network with reward token flows",
    "default": "cryptocurrency market data visualization with blockchain networks"
}

# Palavras a remover do tema para evitar imagens inadequadas
THEME_BLOCKLIST = [
    "hack", "hacker", "attack", "steal", "theft", "scam", "fraud",
    "crash", "collapse", "bankrupt", "death", "dead", "kill",
    "lawsuit", "sue", "arrest", "prison", "jail", "criminal",
    "exploit", "vulnerability", "breach", "leak", "stolen",
    "war", "conflict", "bomb", "terror", "violence"
]


class ImageGenerator:
    """Gerador de imagens v6.0 - Visualização de dados abstratos com sanitização"""

    def __init__(self):
        """Inicializa o gerador de imagens com cliente assíncrono"""
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

        # Configurar Cloudinary
        cloudinary.config(
            cloud_name=settings.CLOUDINARY_CLOUD_NAME,
            api_key=settings.CLOUDINARY_API_KEY,
            api_secret=settings.CLOUDINARY_API_SECRET
        )

    def _sanitize_theme(self, text: str) -> str:
        """
        Remove palavras problemáticas do tema para evitar imagens inadequadas

        Args:
            text: Texto original do tema

        Returns:
            Tema sanitizado
        """
        text_lower = text.lower()
        for word in THEME_BLOCKLIST:
            # Remover palavra e espaços adjacentes
            text_lower = re.sub(rf'\b{word}\b', '', text_lower, flags=re.IGNORECASE)

        # Limpar espaços múltiplos
        text_lower = re.sub(r'\s+', ' ', text_lower).strip()
        return text_lower

    def _extract_theme(self, title: str, content: str, category: Optional[str] = None) -> str:
        """
        Extrai e sanitiza o tema principal da notícia para o prompt

        Args:
            title: Título do artigo
            content: Conteúdo do artigo
            category: Categoria do artigo para fallback

        Returns:
            Tema sanitizado para geração de imagem
        """
        # Sanitizar o título
        sanitized_title = self._sanitize_theme(title)

        # Se o título ficar muito curto após sanitização, usar tema da categoria
        if len(sanitized_title) < 20:
            category_key = category.lower() if category else "default"
            return CATEGORY_VISUAL_THEMES.get(category_key, CATEGORY_VISUAL_THEMES["default"])

        # Limitar tamanho para evitar prompt muito longo
        return sanitized_title[:150]

    async def generate_and_upload_image(
        self,
        title: str,
        content: str,
        category_name: Optional[str] = None
    ) -> str:
        """
        Gera imagem de visualização de dados abstratos (v6.0)

        Args:
            title: Título do artigo
            content: Conteúdo completo do artigo
            category_name: Nome da categoria para ajuste de tema visual

        Returns:
            URL da imagem no Cloudinary
        """
        try:
            logger.info(f"Gerando imagem v6.0 (data visualization) para: {title[:50]}...")

            # Extrair e sanitizar tema da notícia
            theme = self._extract_theme(title, content, category_name)

            # Obter tema visual da categoria como complemento
            category_key = category_name.lower() if category_name else "default"
            category_visual = CATEGORY_VISUAL_THEMES.get(category_key, CATEGORY_VISUAL_THEMES["default"])

            # Construir prompt de visualização de dados abstratos (v6.0)
            # IMPORTANTE: Foco em visualização ABSTRATA, nunca literal
            prompt = f"""Create an abstract, sophisticated data visualization for a cryptocurrency news article.

CONCEPT: {theme}
VISUAL STYLE: {category_visual}

MANDATORY REQUIREMENTS:
- PURELY ABSTRACT: No literal representations of people, objects, or scenes
- DATA-DRIVEN: Focus on charts, graphs, network nodes, data flows
- PROFESSIONAL: Institutional financial terminal aesthetic
- NO TEXT: Do not include any text, numbers, logos, or symbols

COMPOSITION:
- Overlapping layers of technical line charts and candlestick patterns
- Interconnected node networks representing blockchain topology
- Digital data streams and particle flows
- Geometric patterns suggesting market movements

BACKGROUND: Deep dark mode (#0a0a12), subtle circuit board textures, nearly invisible grid

LIGHTING: Internal screen glow, subtle cyan highlights emanating from data lines, shadowy cybernetic atmosphere

COLOR PALETTE:
- Primary: Dark charcoal gray (#1a1a2e), deep navy blue (#0f0f23)
- Accents: Electric cyan (#00d4ff), pale technical gold (#ffd700)
- Highlights: Subtle purple (#7b2cbf) for depth

QUALITY: 8k rendering, ultra high detail, futuristic UI aesthetic, cinematic composition"""

            logger.debug(f"Prompt v6.0 tema: {theme[:100]}...")

            # Gerar imagem com DALL-E 3 (async)
            response = await self.client.images.generate(
                model="dall-e-3",
                prompt=prompt,
                size="1792x1024",  # Widescreen 16:9 para header de artigo
                quality="hd",
                n=1
            )

            image_url = response.data[0].url
            logger.info(f"Imagem gerada com sucesso: {image_url}")

            # Upload para Cloudinary (executar em thread pool para não bloquear)
            loop = asyncio.get_event_loop()
            upload_result = await loop.run_in_executor(
                _cloudinary_executor,
                lambda: cloudinary.uploader.upload(
                    image_url,
                    folder="vivacripto/articles",
                    transformation=[
                        {'width': 1200, 'height': 630, 'crop': 'fill', 'gravity': 'center', 'quality': 'auto:good'}
                    ]
                )
            )

            cloudinary_url = upload_result['secure_url']
            logger.info(f"Upload para Cloudinary concluído: {cloudinary_url}")
            
            return cloudinary_url
            
        except Exception as e:
            logger.error(f"Erro ao gerar/upload imagem v5.0: {e}")
            return ""

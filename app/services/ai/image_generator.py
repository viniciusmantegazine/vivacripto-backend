"""
Image Generation Service - Data Visualization Style v5.0
Gera visualizações de dados abstratas e sofisticadas com estética de terminal financeiro
"""
import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

from openai import AsyncOpenAI
import cloudinary
import cloudinary.uploader

from app.core.config import settings
from app.core.logging import logger

# ThreadPool para operações síncronas do Cloudinary
_cloudinary_executor = ThreadPoolExecutor(max_workers=3)


class ImageGenerator:
    """Gerador de imagens v5.0 - Visualização de dados abstratos"""

    def __init__(self):
        """Inicializa o gerador de imagens com cliente assíncrono"""
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        
        # Configurar Cloudinary
        cloudinary.config(
            cloud_name=settings.CLOUDINARY_CLOUD_NAME,
            api_key=settings.CLOUDINARY_API_KEY,
            api_secret=settings.CLOUDINARY_API_SECRET
        )
    
    def _extract_theme(self, title: str, content: str) -> str:
        """
        Extrai o tema principal da notícia para o prompt
        
        Args:
            title: Título do artigo
            content: Conteúdo do artigo
            
        Returns:
            Tema extraído em inglês
        """
        # Usar título + primeiras linhas do conteúdo para extrair tema
        text_preview = f"{title}. {content[:500]}"
        
        # Simplificar: usar o título traduzido como tema
        # O DALL-E vai interpretar e criar visualização apropriada
        return text_preview
    
    async def generate_and_upload_image(
        self,
        title: str,
        content: str,
        category_name: Optional[str] = None
    ) -> str:
        """
        Gera imagem de visualização de dados abstratos (v5.0)
        
        Args:
            title: Título do artigo
            content: Conteúdo completo do artigo
            category_name: Nome da categoria (não usado nesta versão)
            
        Returns:
            URL da imagem no Cloudinary
        """
        try:
            logger.info(f"Gerando imagem v5.0 (data visualization) para: {title[:50]}...")
            
            # Extrair tema da notícia
            theme = self._extract_theme(title, content)
            
            # Construir prompt de visualização de dados abstratos
            prompt = f"""An abstract and sophisticated data visualization representing {theme}. 

STYLE: Institutional financial terminal aesthetic, data-driven focused, serious and technological. 

COMPOSITION: Overlapping layers of technical line charts, interconnected node networks, and digital data flows. No literal objects or characters. 

BACKGROUND: Dark mode, subtle deep circuit board textures, nearly invisible digital grid. 

LIGHTING: Internal screen light, subtle glow emanating from data lines, shadowy cybernetic environment. 

COLOR PALETTE: Dark monochromatic (charcoal gray, deep navy blue) with precise accents in electric cyan blue and pale technical gold. 

QUALITY: 8k rendering, high complexity, futuristic UI style, no text."""
            
            logger.debug(f"Prompt v5.0 (primeiros 200 chars): {prompt[:200]}...")

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

"""
Image Generation Service - Simple Direct Prompt v4.0
Envia o texto completo da notícia diretamente para o DALL-E sem processamento adicional
"""
from typing import Optional
from openai import OpenAI
import cloudinary
import cloudinary.uploader
from app.core.config import settings
from app.core.logging import logger


class ImageGenerator:
    """Gerador de imagens v4.0 - Prompt direto do texto da notícia"""
    
    def __init__(self):
        """Inicializa o gerador de imagens"""
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        
        # Configurar Cloudinary
        cloudinary.config(
            cloud_name=settings.CLOUDINARY_CLOUD_NAME,
            api_key=settings.CLOUDINARY_API_KEY,
            api_secret=settings.CLOUDINARY_API_SECRET
        )
    
    async def generate_and_upload_image(
        self,
        title: str,
        content: str,
        category_name: Optional[str] = None
    ) -> str:
        """
        Gera imagem usando o texto completo da notícia como prompt (v4.0)
        
        Args:
            title: Título do artigo
            content: Conteúdo completo do artigo
            category_name: Nome da categoria (não usado nesta versão)
            
        Returns:
            URL da imagem no Cloudinary
        """
        try:
            logger.info(f"Gerando imagem v4.0 (prompt direto) para: {title[:50]}...")
            
            # Construir prompt simples: título + conteúdo
            # Limitar o conteúdo para evitar prompts muito longos (DALL-E tem limite de ~4000 chars)
            content_preview = content[:3000] if len(content) > 3000 else content
            
            prompt = f"{title}\n\n{content_preview}"
            
            logger.debug(f"Prompt direto (primeiros 200 chars): {prompt[:200]}...")
            
            # Gerar imagem com DALL-E 3
            response = self.client.images.generate(
                model="dall-e-3",
                prompt=prompt,
                size="1792x1024",  # Widescreen para header de artigo
                quality="hd",
                n=1
            )
            
            image_url = response.data[0].url
            logger.info(f"Imagem gerada com sucesso: {image_url}")
            
            # Upload para Cloudinary
            upload_result = cloudinary.uploader.upload(
                image_url,
                folder="vivacripto/articles",
                transformation=[
                    {'width': 1200, 'height': 630, 'crop': 'fill', 'gravity': 'center', 'quality': 'auto:good'}
                ]
            )
            
            cloudinary_url = upload_result['secure_url']
            logger.info(f"Upload para Cloudinary concluído: {cloudinary_url}")
            
            return cloudinary_url
            
        except Exception as e:
            logger.error(f"Erro ao gerar/upload imagem v4.0: {e}")
            return ""

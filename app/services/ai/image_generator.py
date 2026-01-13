"""
Image Generation Service v7.0 - Smart Context-Aware Image Generation
Gera imagens únicas e relevantes baseadas em análise inteligente do contexto da notícia

Changelog:
- v7.0: Sistema inteligente de análise de contexto e geração de prompts dinâmicos
- v6.0: Visualização de dados abstratos com sanitização
- v5.0: Estilo de terminal financeiro

Recursos:
- Análise automática de categoria, sentimento, tipo e entidades
- Banco de elementos visuais por classificação
- Geração de prompts com variação para evitar repetição
- Logging detalhado para debug
"""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

from openai import AsyncOpenAI
import cloudinary
import cloudinary.uploader

from app.core.config import settings
from app.core.logging import logger
from app.services.ai.smart_prompt_generator import (
    SmartPromptGenerator,
    smart_prompt_generator
)

# ThreadPool para operações síncronas do Cloudinary
_cloudinary_executor = ThreadPoolExecutor(max_workers=3)


class ImageGenerator:
    """
    Gerador de imagens v7.0 - Context-Aware Smart Generation

    Utiliza análise inteligente de contexto para gerar imagens únicas
    e relevantes para cada notícia de criptomoedas.
    """

    # Configurações de geração
    IMAGE_MODEL = "dall-e-3"
    IMAGE_SIZE = "1792x1024"  # Widescreen 16:9 para header de artigo
    IMAGE_QUALITY = "hd"

    # Transformações do Cloudinary para otimização
    CLOUDINARY_TRANSFORMATIONS = [
        {
            'width': 1200,
            'height': 630,
            'crop': 'fill',
            'gravity': 'center',
            'quality': 'auto:good'
        }
    ]

    def __init__(self, prompt_generator: Optional[SmartPromptGenerator] = None):
        """
        Inicializa o gerador de imagens com cliente assíncrono

        Args:
            prompt_generator: Gerador de prompts inteligente (usa singleton se None)
        """
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.prompt_generator = prompt_generator or smart_prompt_generator

        # Configurar Cloudinary
        cloudinary.config(
            cloud_name=settings.CLOUDINARY_CLOUD_NAME,
            api_key=settings.CLOUDINARY_API_KEY,
            api_secret=settings.CLOUDINARY_API_SECRET
        )

        logger.info("ImageGenerator v7.0 inicializado com Smart Prompt Generator")

    async def generate_and_upload_image(
        self,
        title: str,
        content: str,
        category_name: Optional[str] = None
    ) -> str:
        """
        Gera imagem contextualizada usando análise inteligente (v7.0)

        O sistema analisa a notícia para identificar:
        - Categoria principal (Bitcoin, Ethereum, DeFi, etc.)
        - Sentimento (bullish, bearish, neutro, alerta)
        - Tipo de notícia (preço, regulação, tecnologia, etc.)
        - Entidades mencionadas

        Com base nessa análise, gera um prompt único e relevante
        que resulta em imagens profissionais e diferenciadas.

        Args:
            title: Título do artigo
            content: Conteúdo completo do artigo
            category_name: Nome da categoria para ajuste de tema visual

        Returns:
            URL da imagem no Cloudinary ou string vazia em caso de erro
        """
        try:
            logger.info(f"[ImageGen v7.0] Iniciando geração para: {title[:60]}...")

            # 1. Gerar prompt inteligente com metadados
            prompt_result = self.prompt_generator.generate_prompt_with_metadata(
                title=title,
                content=content,
                category=category_name
            )

            prompt = prompt_result['prompt']
            metadata = prompt_result['metadata']

            logger.info(
                f"[ImageGen v7.0] Contexto detectado: "
                f"sentiment={metadata['sentiment']}, "
                f"type={metadata['news_type']}, "
                f"crypto={metadata['primary_crypto']}, "
                f"confidence={metadata['confidence_score']:.2f}"
            )
            logger.debug(f"[ImageGen v7.0] Prompt ({metadata['prompt_length']} chars): {prompt[:300]}...")

            # 2. Gerar imagem com DALL-E 3
            logger.info("[ImageGen v7.0] Chamando DALL-E 3...")
            response = await self.client.images.generate(
                model=self.IMAGE_MODEL,
                prompt=prompt,
                size=self.IMAGE_SIZE,
                quality=self.IMAGE_QUALITY,
                n=1
            )

            image_url = response.data[0].url
            logger.info(f"[ImageGen v7.0] Imagem gerada com sucesso: {image_url[:80]}...")

            # 3. Upload para Cloudinary com otimização
            cloudinary_url = await self._upload_to_cloudinary(image_url)

            logger.info(f"[ImageGen v7.0] Processo completo. URL final: {cloudinary_url[:80]}...")
            return cloudinary_url

        except Exception as e:
            logger.error(f"[ImageGen v7.0] Erro na geração: {e}", exc_info=True)
            return ""

    async def _upload_to_cloudinary(self, image_url: str) -> str:
        """
        Faz upload da imagem para o Cloudinary com transformações

        Args:
            image_url: URL da imagem gerada pelo DALL-E

        Returns:
            URL segura da imagem no Cloudinary
        """
        loop = asyncio.get_event_loop()

        upload_result = await loop.run_in_executor(
            _cloudinary_executor,
            lambda: cloudinary.uploader.upload(
                image_url,
                folder="vivacripto/articles",
                transformation=self.CLOUDINARY_TRANSFORMATIONS
            )
        )

        cloudinary_url = upload_result['secure_url']
        logger.debug(f"[ImageGen v7.0] Upload Cloudinary concluído: {cloudinary_url}")

        return cloudinary_url

    async def generate_image_preview(
        self,
        title: str,
        content: str,
        category_name: Optional[str] = None
    ) -> dict:
        """
        Gera preview do prompt sem criar a imagem (para debug/teste)

        Útil para verificar a análise de contexto e o prompt gerado
        antes de consumir créditos da API de imagem.

        Args:
            title: Título do artigo
            content: Conteúdo do artigo
            category_name: Categoria opcional

        Returns:
            Dict com prompt e metadados completos
        """
        return self.prompt_generator.generate_prompt_with_metadata(
            title=title,
            content=content,
            category=category_name
        )


# Singleton para compatibilidade com código existente
image_generator = ImageGenerator()

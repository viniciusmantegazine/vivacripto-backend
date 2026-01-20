"""
Image Generation Service v9.0 - Gemini + DALL-E Fallback
Gera imagens usando Google Gemini (primário) com DALL-E como fallback

Changelog:
- v9.0: Migração para Gemini como primário, DALL-E como fallback
- v8.0: Estilo editorial fotográfico (CoinDesk/Cointelegraph standard)
- v7.0: Sistema inteligente de análise de contexto e geração de prompts dinâmicos
- v6.0: Visualização de dados abstratos com sanitização
- v5.0: Estilo de terminal financeiro

Recursos:
- Análise de entidade principal (crypto, exchange, bank, government, etc.)
- Elementos visuais CONCRETOS (logos, moedas, prédios) - não abstratos
- Alta legibilidade para texto sobreposto
- Paletas de cores específicas por criptomoeda
"""

import asyncio
import base64
import io
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

from openai import AsyncOpenAI
from PIL import Image
import cloudinary
import cloudinary.uploader

from app.core.config import settings
from app.core.logging import logger
from app.services.ai.smart_prompt_generator import (
    SmartPromptGenerator,
    smart_prompt_generator
)

# Google Gemini imports
try:
    from google import genai
    from google.genai import types
    GEMINI_AVAILABLE = True
    # Verificar se ImageConfig está disponível (pode variar entre versões)
    GEMINI_IMAGE_CONFIG_AVAILABLE = hasattr(types, 'ImageConfig')
except ImportError:
    GEMINI_AVAILABLE = False
    GEMINI_IMAGE_CONFIG_AVAILABLE = False
    logger.warning("Google GenAI SDK não instalado. Usando apenas DALL-E.")

# ThreadPool para operações síncronas do Cloudinary
_cloudinary_executor = ThreadPoolExecutor(max_workers=3)


class ImageGenerator:
    """
    Gerador de imagens v9.0 - Gemini + DALL-E Fallback

    Utiliza Google Gemini como primário e DALL-E como fallback para
    gerar imagens únicas e relevantes para cada notícia de criptomoedas.
    """

    # Configurações de geração - Gemini
    GEMINI_IMAGE_MODEL = "gemini-3-pro-image-preview"
    GEMINI_ASPECT_RATIO = "16:9"
    GEMINI_IMAGE_SIZE = "2K"

    # Configurações de geração - DALL-E (fallback)
    DALLE_MODEL = "dall-e-3"
    DALLE_SIZE = "1792x1024"  # Widescreen 16:9 para header de artigo
    DALLE_QUALITY = "hd"

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
        Inicializa o gerador de imagens com clientes Gemini e OpenAI

        Args:
            prompt_generator: Gerador de prompts inteligente (usa singleton se None)
        """
        # OpenAI/DALL-E client (fallback)
        self.openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.prompt_generator = prompt_generator or smart_prompt_generator

        # Gemini client (primário)
        self.gemini_client = None
        self.use_gemini = False

        if GEMINI_AVAILABLE and settings.GEMINI_API_KEY:
            try:
                self.gemini_client = genai.Client(api_key=settings.GEMINI_API_KEY)
                self.use_gemini = True
                logger.info("ImageGenerator v9.0: Gemini configurado como primário")
            except Exception as e:
                logger.warning(f"Falha ao inicializar Gemini para imagens: {e}. Usando DALL-E como primário.")
        else:
            logger.info("ImageGenerator v9.0: Usando DALL-E (Gemini não disponível)")

        # Configurar Cloudinary
        cloudinary.config(
            cloud_name=settings.CLOUDINARY_CLOUD_NAME,
            api_key=settings.CLOUDINARY_API_KEY,
            api_secret=settings.CLOUDINARY_API_SECRET
        )

        logger.info("ImageGenerator v9.0 inicializado com Editorial Prompt Generator")

    async def generate_and_upload_image(
        self,
        title: str,
        content: str,
        category_name: Optional[str] = None
    ) -> str:
        """
        Gera imagem usando Gemini (primário) ou DALL-E (fallback)

        O sistema analisa a notícia para identificar:
        - Entidade principal (Bitcoin, JPMorgan, SEC, etc.)
        - Tipo de entidade (crypto, bank, government, exchange, etc.)
        - Sentimento (positive, negative, neutral)
        - Ação (lança, sobe, cai, alerta, etc.)

        Com base nessa análise, gera um prompt EDITORIAL FOTOGRÁFICO
        no padrão CoinDesk/Cointelegraph com elementos visuais concretos.

        Args:
            title: Título do artigo
            content: Conteúdo completo do artigo
            category_name: Nome da categoria para ajuste de tema visual

        Returns:
            URL da imagem no Cloudinary ou string vazia em caso de erro
        """
        try:
            logger.info(f"[ImageGen v9.0] Iniciando geração para: {title[:60]}...")

            # 1. Gerar prompt editorial com metadados
            prompt_result = self.prompt_generator.generate_prompt_with_metadata(
                title=title,
                content=content,
                category=category_name
            )

            prompt = prompt_result['prompt']
            metadata = prompt_result['metadata']

            logger.info(
                f"[ImageGen v9.0] Contexto detectado: "
                f"entity={metadata['entity_type']}:{metadata['primary_entity']}, "
                f"sentiment={metadata['sentiment']}, "
                f"action={metadata['action']}, "
                f"confidence={metadata['confidence_score']:.2f}"
            )
            logger.debug(f"[ImageGen v9.0] Prompt ({metadata['prompt_length']} chars): {prompt[:300]}...")

            # 2. Tentar gerar imagem com Gemini primeiro
            gemini_result = None

            if self.use_gemini and self.gemini_client:
                try:
                    logger.info(f"[ImageGen v9.0] Chamando Gemini ({self.GEMINI_IMAGE_MODEL})...")
                    gemini_result = await self._generate_with_gemini(prompt)
                    if gemini_result:
                        logger.info("[ImageGen v9.0] Imagem gerada com sucesso via Gemini")
                except Exception as e:
                    logger.warning(f"[ImageGen v9.0] Falha no Gemini: {e}. Tentando DALL-E...")

            # 3. Fallback para DALL-E se Gemini falhou
            if gemini_result is None:
                try:
                    logger.info(f"[ImageGen v9.0] Chamando DALL-E ({self.DALLE_MODEL})...")
                    image_url = await self._generate_with_dalle(prompt)
                    if image_url:
                        logger.info(f"[ImageGen v9.0] Imagem gerada via DALL-E: {image_url[:80]}...")
                        # Upload URL diretamente para Cloudinary
                        cloudinary_url = await self._upload_to_cloudinary(image_url)
                        logger.info(f"[ImageGen v9.0] Processo completo. URL final: {cloudinary_url[:80]}...")
                        return cloudinary_url
                except Exception as e:
                    logger.error(f"[ImageGen v9.0] Falha no DALL-E: {e}")
                    return ""

            # 4. Upload bytes do Gemini para Cloudinary
            if gemini_result:
                image_bytes, mime_type = gemini_result
                cloudinary_url = await self._upload_bytes_to_cloudinary(image_bytes, mime_type)
                logger.info(f"[ImageGen v9.0] Processo completo. URL final: {cloudinary_url[:80]}...")
                return cloudinary_url

            return ""

        except Exception as e:
            logger.error(f"[ImageGen v9.0] Erro na geração: {e}", exc_info=True)
            return ""

    async def _generate_with_gemini(self, prompt: str) -> Optional[tuple[bytes, str]]:
        """
        Gera imagem usando Google Gemini

        Args:
            prompt: Prompt para geração da imagem

        Returns:
            Tuple (bytes da imagem, mime_type) ou None em caso de erro
        """
        # Construir config - usar apenas aspect_ratio (image_size não é suportado em todas versões)
        if GEMINI_IMAGE_CONFIG_AVAILABLE:
            config = types.GenerateContentConfig(
                response_modalities=['IMAGE'],
                image_config=types.ImageConfig(
                    aspect_ratio=self.GEMINI_ASPECT_RATIO
                )
            )
        else:
            # Fallback: usar apenas response_modalities sem image_config
            config = types.GenerateContentConfig(
                response_modalities=['IMAGE'],
            )
            logger.debug("[ImageGen v9.0] ImageConfig não disponível, usando config básico")

        response = await self.gemini_client.aio.models.generate_content(
            model=self.GEMINI_IMAGE_MODEL,
            contents=prompt,
            config=config,
        )

        # Extrair imagem da resposta
        for part in response.candidates[0].content.parts:
            if part.inline_data is not None:
                inline_data = part.inline_data
                mime_type = getattr(inline_data, 'mime_type', 'image/png')
                raw_data = inline_data.data

                logger.debug(f"[ImageGen v9.0] Gemini inline_data: mime_type={mime_type}, data_type={type(raw_data).__name__}, data_len={len(raw_data) if raw_data else 0}")

                # O SDK do Gemini pode retornar dados como string base64 ou bytes
                # Verificar e converter conforme necessário
                if isinstance(raw_data, str):
                    # Dados retornados como string base64 - decodificar
                    logger.debug("[ImageGen v9.0] Decodificando dados base64 do Gemini")
                    image_bytes = base64.b64decode(raw_data)
                elif isinstance(raw_data, bytes):
                    # Já são bytes - usar diretamente
                    image_bytes = raw_data
                else:
                    logger.warning(f"[ImageGen v9.0] Tipo de dado inesperado do Gemini: {type(raw_data)}")
                    return None

                logger.debug(f"[ImageGen v9.0] Imagem processada: {len(image_bytes)} bytes")
                return (image_bytes, mime_type)

        return None

    async def _generate_with_dalle(self, prompt: str) -> Optional[str]:
        """
        Gera imagem usando DALL-E

        Args:
            prompt: Prompt para geração da imagem

        Returns:
            URL da imagem gerada ou None em caso de erro
        """
        response = await self.openai_client.images.generate(
            model=self.DALLE_MODEL,
            prompt=prompt,
            size=self.DALLE_SIZE,
            quality=self.DALLE_QUALITY,
            n=1
        )

        return response.data[0].url

    async def _upload_bytes_to_cloudinary(self, image_bytes: bytes, mime_type: str = "image/png") -> str:
        """
        Faz upload de bytes de imagem para o Cloudinary

        Args:
            image_bytes: Bytes da imagem gerada
            mime_type: Tipo MIME da imagem (ex: image/png, image/jpeg)

        Returns:
            URL segura da imagem no Cloudinary
        """
        loop = asyncio.get_event_loop()

        logger.debug(f"[ImageGen v9.0] Preparando upload: {len(image_bytes)} bytes, mime={mime_type}")
        logger.debug(f"[ImageGen v9.0] Primeiros 20 bytes (hex): {image_bytes[:20].hex() if len(image_bytes) >= 20 else image_bytes.hex()}")

        # Validar e converter imagem usando Pillow para garantir formato correto
        try:
            img = Image.open(io.BytesIO(image_bytes))
            logger.debug(f"[ImageGen v9.0] Pillow detectou: format={img.format}, mode={img.mode}, size={img.size}")

            # Converter para RGB se necessário (RGBA pode causar problemas)
            if img.mode in ('RGBA', 'LA', 'P'):
                img = img.convert('RGB')
                logger.debug(f"[ImageGen v9.0] Convertido para RGB")

            # Salvar como PNG em buffer
            output_buffer = io.BytesIO()
            img.save(output_buffer, format='PNG', optimize=True)
            output_buffer.seek(0)
            validated_bytes = output_buffer.getvalue()

            logger.debug(f"[ImageGen v9.0] Imagem validada: {len(validated_bytes)} bytes (PNG)")

        except Exception as e:
            logger.error(f"[ImageGen v9.0] Pillow não conseguiu abrir imagem: {e}")
            raise ValueError(f"Invalid image data from Gemini: {e}")

        # Criar data URI com os bytes validados
        base64_data = base64.b64encode(validated_bytes).decode('utf-8')
        data_uri = f"data:image/png;base64,{base64_data}"

        logger.debug(f"[ImageGen v9.0] Data URI criado: {len(data_uri)} chars")

        upload_result = await loop.run_in_executor(
            _cloudinary_executor,
            lambda: cloudinary.uploader.upload(
                data_uri,
                folder="vivacripto/articles",
                format="png",
                transformation=self.CLOUDINARY_TRANSFORMATIONS
            )
        )

        cloudinary_url = upload_result['secure_url']
        logger.debug(f"[ImageGen v9.0] Upload Cloudinary (bytes) concluído: {cloudinary_url}")

        return cloudinary_url

    async def _upload_to_cloudinary(self, image_url: str) -> str:
        """
        Faz upload da imagem para o Cloudinary com transformações

        Args:
            image_url: URL da imagem gerada

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
        logger.debug(f"[ImageGen v9.0] Upload Cloudinary concluído: {cloudinary_url}")

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

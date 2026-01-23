"""
Image Generation Service v10.0 - AI-Powered Contextual Image Generation
Gera imagens usando Google Gemini (primário) com DALL-E como fallback

## NOVIDADE v10.0: GERAÇÃO CONTEXTUAL VIA IA

A partir da v10.0, o sistema usa análise contextual profunda via IA para gerar
prompts que CONTAM A HISTÓRIA da notícia, não apenas mostram logos genéricos.

O método principal `generate_and_upload_image()` agora usa por padrão:
1. Análise contextual do CONTEÚDO COMPLETO da notícia via Gemini
2. Construção de prompt narrativo baseado na história real
3. Geração de imagem via Gemini (ou DALL-E como fallback)

### EXEMPLO DE DIFERENÇA:

**ANTES (v9.x):**
Título: "SEC aprova ETF de Bitcoin"
Prompt: "SEC logo, Bitcoin coin, approval stamp, institutional setting"
Resultado: Imagem genérica

**DEPOIS (v10.0):**
Título: "SEC aprova ETF de Bitcoin"
Conteúdo: "Gary Gensler anunciou... BlackRock será a primeira... NYSE..."
Prompt: "Gary Gensler at SEC podium, BlackRock branding, NYSE trading floor,
        Bitcoin symbol prominent, historic approval celebration"
Resultado: Imagem que CONTA A HISTÓRIA

Changelog:
- v10.0: Integração com análise contextual via IA (ContextualImageAnalyzer)
       - Novo método generate_and_upload_image() usa prompt contextual por padrão
       - Adicionado parâmetro use_contextual_analysis para controle
       - Mantida compatibilidade total com modo legacy
- v9.1: Melhorias de robustez, logging detalhado, fallback aprimorado
- v9.0: Migração para Gemini como primário, DALL-E como fallback
- v8.0: Estilo editorial fotográfico (CoinDesk/Cointelegraph standard)
- v7.0: Sistema inteligente de análise de contexto e geração de prompts dinâmicos

Recursos:
- ANÁLISE CONTEXTUAL PROFUNDA via IA (NOVO v10.0)
- Análise de entidade principal (crypto, exchange, bank, government, etc.)
- Elementos visuais CONCRETOS (logos, moedas, prédios) - não abstratos
- Alta legibilidade para texto sobreposto
- Paletas de cores específicas por criptomoeda
"""

import atexit
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

# Registrar shutdown do executor para evitar resource leaks
atexit.register(_cloudinary_executor.shutdown, wait=False)


class ImageGenerator:
    """
    Gerador de imagens v10.0 - AI-Powered Contextual Image Generation

    Utiliza Google Gemini como primário e DALL-E como fallback para
    gerar imagens únicas e relevantes para cada notícia de criptomoedas.

    ## NOVIDADE v10.0: GERAÇÃO CONTEXTUAL VIA IA

    O método `generate_and_upload_image()` agora usa por padrão análise contextual
    profunda via IA para gerar prompts que CONTAM A HISTÓRIA da notícia.

    Para usar o modo legacy (baseado em regex), defina use_contextual_analysis=False.
    """

    # Configurações de geração - Gemini
    GEMINI_IMAGE_MODEL = "gemini-3-pro-image-preview"
    GEMINI_ASPECT_RATIO = "16:9"

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
                logger.info("ImageGenerator v9.1: Gemini configurado como primário")
            except Exception as e:
                logger.warning(f"Falha ao inicializar Gemini para imagens: {e}. Usando DALL-E como primário.")
        else:
            logger.info("ImageGenerator v9.1: Usando DALL-E (Gemini não disponível)")

        # Configurar Cloudinary
        cloudinary.config(
            cloud_name=settings.CLOUDINARY_CLOUD_NAME,
            api_key=settings.CLOUDINARY_API_KEY,
            api_secret=settings.CLOUDINARY_API_SECRET
        )

        logger.info("ImageGenerator v9.1 inicializado com Editorial Prompt Generator")

    async def generate_and_upload_image(
        self,
        title: str,
        content: str,
        category_name: Optional[str] = None,
        use_contextual_analysis: bool = True
    ) -> str:
        """
        Gera imagem usando Gemini (primário) ou DALL-E (fallback)

        ## v10.0: ANÁLISE CONTEXTUAL VIA IA (PADRÃO)

        Por padrão, o sistema agora usa análise contextual profunda via IA
        para gerar prompts que CONTAM A HISTÓRIA da notícia visualmente.

        O sistema analisa o CONTEÚDO COMPLETO da notícia para identificar:
        - História principal e conceito visual
        - Pessoas mencionadas (CEOs, reguladores, etc.)
        - Instituições envolvidas (SEC, BlackRock, NYSE, etc.)
        - Criptomoedas específicas mencionadas
        - Evento concreto que aconteceu
        - Tom e importância da notícia

        Com base nessa análise, gera um prompt NARRATIVO EDITORIAL
        que representa visualmente a história real da notícia.

        Args:
            title: Título do artigo
            content: Conteúdo COMPLETO do artigo (quanto mais, melhor)
            category_name: Nome da categoria para ajuste de tema visual
            use_contextual_analysis: Se True (padrão), usa análise via IA.
                                     Se False, usa modo legacy (regex).

        Returns:
            URL da imagem no Cloudinary ou string vazia em caso de erro
        """
        try:
            logger.info(f"[ImageGen v10.0] Iniciando geração para: {title[:60]}...")

            # 1. Gerar prompt - contextual (v10.0) ou legacy (v9.x)
            if use_contextual_analysis:
                logger.info("[ImageGen v10.0] Usando análise contextual via IA...")
                prompt_result = await self.prompt_generator.generate_prompt_with_metadata_contextual(
                    title=title,
                    content=content,
                    category=category_name
                )
            else:
                logger.info("[ImageGen v10.0] Usando análise legacy (regex)...")
                prompt_result = self.prompt_generator.generate_prompt_with_metadata(
                    title=title,
                    content=content,
                    category=category_name
                )

            prompt = prompt_result['prompt']
            metadata = prompt_result['metadata']

            # Log de contexto detectado
            if use_contextual_analysis and 'story_summary' in metadata:
                logger.info(
                    f"[ImageGen v10.0] Contexto via IA: "
                    f"story='{metadata.get('story_summary', '')[:50]}...', "
                    f"cryptos={metadata.get('cryptocurrencies', [])}, "
                    f"institutions={metadata.get('institutions', [])[:2]}, "
                    f"tone={metadata.get('tone', 'neutral')}, "
                    f"confidence={metadata.get('confidence_score', 0):.2f}"
                )
            else:
                logger.info(
                    f"[ImageGen v10.0] Contexto legacy: "
                    f"entity={metadata.get('entity_type', 'unknown')}:{metadata.get('primary_entity', 'unknown')}, "
                    f"sentiment={metadata.get('sentiment', 'neutral')}, "
                    f"action={metadata.get('action', 'unknown')}, "
                    f"confidence={metadata.get('confidence_score', 0):.2f}"
                )

            logger.debug(f"[ImageGen v10.0] Prompt ({metadata.get('prompt_length', len(prompt))} chars): {prompt[:300]}...")

            # 2. Tentar gerar imagem com Gemini primeiro
            gemini_result = None
            use_dalle_fallback = False

            if self.use_gemini and self.gemini_client:
                try:
                    logger.info(f"[ImageGen v10.0] Chamando Gemini ({self.GEMINI_IMAGE_MODEL})...")
                    gemini_result = await self._generate_with_gemini(prompt)
                    if gemini_result:
                        logger.info("[ImageGen v10.0] Imagem gerada com sucesso via Gemini")
                        # Tentar fazer upload para Cloudinary
                        try:
                            image_bytes, mime_type = gemini_result
                            cloudinary_url = await self._upload_bytes_to_cloudinary(image_bytes, mime_type)
                            logger.info(f"[ImageGen v10.0] Processo completo. URL final: {cloudinary_url[:80]}...")
                            return cloudinary_url
                        except Exception as upload_error:
                            logger.warning(f"[ImageGen v10.0] Falha no upload Cloudinary: {upload_error}. Tentando DALL-E...")
                            use_dalle_fallback = True
                    else:
                        use_dalle_fallback = True
                except Exception as e:
                    logger.warning(f"[ImageGen v10.0] Falha no Gemini: {e}. Tentando DALL-E...")
                    use_dalle_fallback = True
            else:
                use_dalle_fallback = True

            # 3. Fallback para DALL-E se Gemini falhou ou upload falhou
            if use_dalle_fallback or gemini_result is None:
                try:
                    logger.info(f"[ImageGen v10.0] Chamando DALL-E ({self.DALLE_MODEL})...")
                    image_url = await self._generate_with_dalle(prompt)
                    if image_url:
                        logger.info(f"[ImageGen v10.0] Imagem gerada via DALL-E: {image_url[:80]}...")
                        # Upload URL diretamente para Cloudinary
                        cloudinary_url = await self._upload_to_cloudinary(image_url)
                        logger.info(f"[ImageGen v10.0] Processo completo. URL final: {cloudinary_url[:80]}...")
                        return cloudinary_url
                except Exception as e:
                    logger.error(f"[ImageGen v10.0] Falha no DALL-E: {e}")
                    return ""

            return ""

        except Exception as e:
            logger.error(f"[ImageGen v10.0] Erro na geração: {e}", exc_info=True)
            return ""

    async def _generate_with_gemini(self, prompt: str) -> Optional[tuple[bytes, str]]:
        """
        Gera imagem usando Google Gemini

        Args:
            prompt: Prompt para geração da imagem

        Returns:
            Tuple (bytes da imagem, mime_type) ou None em caso de erro
        """
        # Construir config - usar apenas aspect_ratio
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
            logger.debug("[ImageGen v10.0] ImageConfig não disponível, usando config básico")

        response = await self.gemini_client.aio.models.generate_content(
            model=self.GEMINI_IMAGE_MODEL,
            contents=prompt,
            config=config,
        )

        # Verificar se há candidatos na resposta
        if not response.candidates:
            logger.warning("[ImageGen v10.0] Gemini não retornou candidatos")
            return None

        if not response.candidates[0].content or not response.candidates[0].content.parts:
            logger.warning("[ImageGen v10.0] Gemini retornou resposta sem partes de conteúdo")
            return None

        # Extrair imagem da resposta
        for part in response.candidates[0].content.parts:
            if part.inline_data is not None:
                inline_data = part.inline_data

                # Obter mime_type com verificação robusta
                mime_type = getattr(inline_data, 'mime_type', None)
                if not mime_type:
                    logger.warning("[ImageGen v10.0] Gemini não informou mime_type, usando image/png")
                    mime_type = 'image/png'

                raw_data = inline_data.data

                # Verificar se raw_data existe
                if not raw_data:
                    logger.error("[ImageGen v10.0] Gemini retornou inline_data.data vazio")
                    return None

                # Log detalhado do tipo e tamanho dos dados
                data_type = type(raw_data).__name__
                data_len = len(raw_data) if hasattr(raw_data, '__len__') else 'unknown'
                logger.info(f"[ImageGen v10.0] Gemini inline_data: mime_type={mime_type}, data_type={data_type}, data_len={data_len}")

                # O SDK do Gemini pode retornar dados como string base64 ou bytes
                if isinstance(raw_data, str):
                    # Dados retornados como string base64 - decodificar
                    logger.debug("[ImageGen v10.0] Decodificando dados base64 do Gemini")
                    try:
                        image_bytes = base64.b64decode(raw_data)
                    except Exception as decode_error:
                        logger.error(f"[ImageGen v10.0] Erro ao decodificar base64: {decode_error}")
                        return None
                elif isinstance(raw_data, bytes):
                    # Já são bytes - usar diretamente
                    image_bytes = raw_data
                else:
                    # Tentar converter para bytes
                    logger.warning(f"[ImageGen v10.0] Tipo de dado inesperado: {data_type}, tentando converter")
                    try:
                        if hasattr(raw_data, 'read'):
                            image_bytes = raw_data.read()
                        elif hasattr(raw_data, '__bytes__'):
                            image_bytes = bytes(raw_data)
                        else:
                            logger.error(f"[ImageGen v10.0] Não foi possível converter {data_type} para bytes")
                            return None
                    except Exception as conv_error:
                        logger.error(f"[ImageGen v10.0] Erro na conversão: {conv_error}")
                        return None

                # Verificar se temos bytes válidos
                if not image_bytes or len(image_bytes) < 100:
                    logger.error(f"[ImageGen v10.0] Bytes inválidos: {len(image_bytes) if image_bytes else 0} bytes")
                    return None

                # Log dos primeiros bytes para diagnóstico (magic bytes)
                hex_preview = image_bytes[:16].hex()
                logger.info(f"[ImageGen v10.0] Magic bytes (hex): {hex_preview}")

                # Verificar se parece ser base64 encoded (bytes começam com caracteres ASCII imprimíveis)
                # Base64 geralmente começa com letras/números, não com bytes binários
                first_bytes = image_bytes[:100]
                try:
                    first_chars = first_bytes.decode('ascii')
                    # Se conseguiu decodificar como ASCII e parece base64, tentar decodificar
                    if all(c in 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=' for c in first_chars.replace('\n', '').replace('\r', '')):
                        logger.warning("[ImageGen v10.0] Dados parecem ser base64 double-encoded, decodificando...")
                        try:
                            image_bytes = base64.b64decode(image_bytes)
                            logger.info(f"[ImageGen v10.0] Após decodificação base64: {len(image_bytes)} bytes")
                            hex_preview = image_bytes[:16].hex()
                            logger.info(f"[ImageGen v10.0] Magic bytes após decode (hex): {hex_preview}")
                        except Exception as e:
                            logger.warning(f"[ImageGen v10.0] Falha ao decodificar como base64: {e}")
                except (UnicodeDecodeError, AttributeError):
                    # Bytes binários normais, não é base64
                    pass

                # Identificar formato real pelos magic bytes
                detected_format = self._detect_image_format(image_bytes)
                if detected_format:
                    logger.info(f"[ImageGen v10.0] Formato detectado pelos magic bytes: {detected_format}")
                    # Atualizar mime_type se detectado diferente
                    format_to_mime = {
                        'PNG': 'image/png',
                        'JPEG': 'image/jpeg',
                        'WEBP': 'image/webp',
                        'GIF': 'image/gif',
                    }
                    if detected_format in format_to_mime:
                        mime_type = format_to_mime[detected_format]
                else:
                    logger.warning(f"[ImageGen v10.0] Formato não reconhecido pelos magic bytes. Primeiros 50 bytes: {image_bytes[:50]}")

                logger.info(f"[ImageGen v10.0] Imagem processada: {len(image_bytes)} bytes, mime={mime_type}")
                return (image_bytes, mime_type)

        logger.warning("[ImageGen v10.0] Nenhuma imagem encontrada na resposta do Gemini")
        return None

    def _detect_image_format(self, data: bytes) -> Optional[str]:
        """
        Detecta o formato da imagem pelos magic bytes

        Args:
            data: Bytes da imagem

        Returns:
            Nome do formato ou None se não reconhecido
        """
        if len(data) < 8:
            return None

        # PNG: 89 50 4E 47 0D 0A 1A 0A
        if data[:8] == b'\x89PNG\r\n\x1a\n':
            return 'PNG'

        # JPEG: FF D8 FF
        if data[:3] == b'\xff\xd8\xff':
            return 'JPEG'

        # WebP: 52 49 46 46 ... 57 45 42 50 (RIFF...WEBP)
        if data[:4] == b'RIFF' and data[8:12] == b'WEBP':
            return 'WEBP'

        # GIF: 47 49 46 38
        if data[:4] == b'GIF8':
            return 'GIF'

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

        Raises:
            ValueError: Se a imagem não puder ser processada
        """
        loop = asyncio.get_running_loop()

        logger.debug(f"[ImageGen v10.0] Preparando upload: {len(image_bytes)} bytes, mime={mime_type}")

        # Validar e converter imagem usando Pillow para garantir formato correto
        validated_bytes = None
        try:
            img = Image.open(io.BytesIO(image_bytes))
            logger.info(f"[ImageGen v10.0] Pillow detectou: format={img.format}, mode={img.mode}, size={img.size}")

            # Converter para RGB se necessário (RGBA pode causar problemas)
            if img.mode in ('RGBA', 'LA', 'P'):
                # Criar background branco para transparência
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                img = background
                logger.debug("[ImageGen v10.0] Convertido para RGB com fundo branco")
            elif img.mode != 'RGB':
                img = img.convert('RGB')
                logger.debug(f"[ImageGen v10.0] Convertido de {img.mode} para RGB")

            # Salvar como PNG em buffer
            output_buffer = io.BytesIO()
            img.save(output_buffer, format='PNG', optimize=True)
            output_buffer.seek(0)
            validated_bytes = output_buffer.getvalue()

            logger.info(f"[ImageGen v10.0] Imagem validada: {len(validated_bytes)} bytes (PNG)")

        except Exception as e:
            logger.warning(f"[ImageGen v10.0] Pillow não conseguiu processar imagem: {e}")
            # Fallback: tentar upload direto sem validação Pillow
            logger.info("[ImageGen v10.0] Tentando upload direto sem validação Pillow...")
            validated_bytes = image_bytes

        if not validated_bytes:
            raise ValueError("No valid image bytes to upload")

        # Determinar formato para o upload
        # Se Pillow processou, é PNG; se não, usar o mime_type original
        upload_mime = "image/png" if validated_bytes != image_bytes else mime_type
        upload_format = "png" if upload_mime == "image/png" else mime_type.split('/')[-1]

        # Criar data URI com os bytes
        base64_data = base64.b64encode(validated_bytes).decode('utf-8')
        data_uri = f"data:{upload_mime};base64,{base64_data}"

        logger.info(f"[ImageGen v10.0] Data URI criado: {len(data_uri)} chars, format={upload_format}")

        upload_result = await loop.run_in_executor(
            _cloudinary_executor,
            lambda: cloudinary.uploader.upload(
                data_uri,
                folder="vivacripto/articles",
                format=upload_format,
                transformation=self.CLOUDINARY_TRANSFORMATIONS
            )
        )

        cloudinary_url = upload_result['secure_url']
        logger.info(f"[ImageGen v10.0] Upload Cloudinary (bytes) concluído: {cloudinary_url}")

        return cloudinary_url

    async def _upload_to_cloudinary(self, image_url: str) -> str:
        """
        Faz upload da imagem para o Cloudinary com transformações

        Args:
            image_url: URL da imagem gerada

        Returns:
            URL segura da imagem no Cloudinary
        """
        loop = asyncio.get_running_loop()

        upload_result = await loop.run_in_executor(
            _cloudinary_executor,
            lambda: cloudinary.uploader.upload(
                image_url,
                folder="vivacripto/articles",
                transformation=self.CLOUDINARY_TRANSFORMATIONS
            )
        )

        cloudinary_url = upload_result['secure_url']
        logger.info(f"[ImageGen v10.0] Upload Cloudinary concluído: {cloudinary_url}")

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


# Lazy initialization para evitar problemas com variáveis de ambiente
_image_generator: Optional[ImageGenerator] = None


def get_image_generator() -> ImageGenerator:
    """
    Retorna instância do ImageGenerator (lazy initialization)

    Returns:
        Instância singleton do ImageGenerator
    """
    global _image_generator
    if _image_generator is None:
        _image_generator = ImageGenerator()
    return _image_generator


# Manter compatibilidade com código existente que usa o singleton diretamente
# Nota: Em novos códigos, preferir usar get_image_generator()
image_generator = ImageGenerator()

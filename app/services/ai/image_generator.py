"""
AI Image Generator Service
Gera imagens com DALL-E 3 e faz upload para Cloudinary
"""
from typing import Optional
from openai import AsyncOpenAI
import cloudinary
import cloudinary.uploader
from loguru import logger
import httpx

from app.core.config import settings


class ImageGenerator:
    """Gerador de imagens com IA"""
    
    def __init__(self):
        self.openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        
        # Configurar Cloudinary
        cloudinary.config(
            cloud_name=settings.CLOUDINARY_CLOUD_NAME,
            api_key=settings.CLOUDINARY_API_KEY,
            api_secret=settings.CLOUDINARY_API_SECRET,
        )
    
    async def generate_and_upload_image(
        self, 
        article_title: str,
        article_content: str
    ) -> Optional[str]:
        """
        Gera uma imagem ilustrativa e faz upload para Cloudinary
        
        Args:
            article_title: Título do artigo
            article_content: Conteúdo do artigo
            
        Returns:
            URL da imagem no Cloudinary ou None se falhar
        """
        try:
            logger.info(f"Gerando imagem para: {article_title[:50]}...")
            
            # Gerar imagem com DALL-E 3
            image_url = await self._generate_image(article_title, article_content)
            
            if not image_url:
                logger.warning("Falha ao gerar imagem")
                return None
            
            # Fazer upload para Cloudinary
            cloudinary_url = await self._upload_to_cloudinary(image_url, article_title)
            
            if cloudinary_url:
                logger.info(f"Imagem gerada e enviada: {cloudinary_url}")
            
            return cloudinary_url
        
        except Exception as e:
            logger.error(f"Erro ao gerar e enviar imagem: {e}")
            return None
    
    async def _generate_image(
        self, 
        title: str, 
        content: str
    ) -> Optional[str]:
        """Gera imagem usando DALL-E 3"""
        # Criar prompt para a imagem
        prompt = self._create_image_prompt(title, content)
        
        try:
            response = await self.openai_client.images.generate(
                model="dall-e-3",
                prompt=prompt,
                size="1792x1024",  # Landscape
                quality="standard",  # "standard" ou "hd"
                n=1,
            )
            
            image_url = response.data[0].url
            return image_url
        
        except Exception as e:
            logger.error(f"Erro ao gerar imagem com DALL-E: {e}")
            return None
    
    def _create_image_prompt(self, title: str, content: str) -> str:
        """Cria prompt otimizado para geração de imagem"""
        # Extrair tema principal
        theme_keywords = self._extract_theme_keywords(title, content)
        
        prompt = f"""Create a modern, professional illustration for a cryptocurrency news article.

Theme: {theme_keywords}

Style requirements:
- Digital art, modern and clean
- Cryptocurrency/blockchain themed
- Abstract and illustrative (NOT photorealistic)
- Professional and trustworthy aesthetic
- Vibrant but not overwhelming colors
- Suitable for a news website header

NO text, NO logos, NO specific people or brands."""

        return prompt
    
    def _extract_theme_keywords(self, title: str, content: str) -> str:
        """Extrai palavras-chave temáticas para o prompt"""
        # Palavras-chave comuns em cripto
        crypto_themes = {
            "bitcoin": "Bitcoin blockchain technology",
            "ethereum": "Ethereum smart contracts",
            "defi": "Decentralized finance",
            "nft": "NFT digital art",
            "trading": "Cryptocurrency trading",
            "mining": "Crypto mining",
            "blockchain": "Blockchain technology",
            "web3": "Web3 decentralization",
            "altcoin": "Alternative cryptocurrencies",
            "market": "Crypto market analysis",
        }
        
        text = f"{title} {content}".lower()
        
        # Encontrar tema mais relevante
        for keyword, theme in crypto_themes.items():
            if keyword in text:
                return theme
        
        # Tema padrão
        return "Cryptocurrency and blockchain technology"
    
    async def _upload_to_cloudinary(
        self, 
        image_url: str, 
        title: str
    ) -> Optional[str]:
        """Faz upload da imagem para Cloudinary"""
        try:
            # Baixar imagem do DALL-E
            async with httpx.AsyncClient() as client:
                response = await client.get(image_url)
                response.raise_for_status()
                image_data = response.content
            
            # Upload para Cloudinary
            result = cloudinary.uploader.upload(
                image_data,
                folder="vivacripto/posts",
                resource_type="image",
                format="webp",  # Formato otimizado
                transformation=[
                    {"width": 1200, "height": 630, "crop": "fill"},  # Open Graph size
                    {"quality": "auto:good"},
                    {"fetch_format": "auto"},
                ],
            )
            
            return result.get("secure_url")
        
        except Exception as e:
            logger.error(f"Erro ao fazer upload para Cloudinary: {e}")
            return None

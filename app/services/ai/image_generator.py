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
        """Cria prompt otimizado e contextual para geração de imagem"""
        # Extrair contexto detalhado do artigo
        context = self._extract_detailed_context(title, content)
        
        prompt = f"""Create a modern, professional illustration for a cryptocurrency news article.

Article Context: {context['description']}

Main Subject: {context['subject']}
Key Elements: {', '.join(context['elements'])}
Visual Style: {context['style']}

Style Requirements:
- Digital art, modern and clean aesthetic
- {context['color_scheme']} color palette
- Abstract and illustrative (NOT photorealistic)
- Professional and trustworthy look
- Suitable for a news website header image
- Focus on {context['focus']}

Technical Requirements:
- NO text, NO logos, NO specific people faces
- NO brand names or trademarks
- Landscape orientation (16:9)
- High contrast for readability

Mood: {context['mood']}"""

        logger.info(f"Image prompt generated - Subject: {context['subject']}, Focus: {context['focus']}")
        return prompt
    
    def _extract_detailed_context(self, title: str, content: str) -> dict:
        """Extrai contexto detalhado do artigo para prompt específico"""
        text = f"{title} {content[:500]}".lower()  # Primeiros 500 chars do conteúdo
        
        # Detectar criptomoeda/projeto específico
        crypto_projects = {
            "bitcoin": {
                "subject": "Bitcoin",
                "elements": ["Bitcoin symbol", "blockchain network", "digital gold"],
                "style": "Bold and iconic",
                "color_scheme": "Orange and gold tones",
                "focus": "Bitcoin's dominance and value",
                "mood": "Confident and established"
            },
            "ethereum": {
                "subject": "Ethereum",
                "elements": ["Ethereum logo concept", "smart contracts", "decentralized apps"],
                "style": "Futuristic and technological",
                "color_scheme": "Purple and blue gradients",
                "focus": "Smart contract innovation",
                "mood": "Innovative and progressive"
            },
            "solana": {
                "subject": "Solana",
                "elements": ["High-speed network", "scalability", "modern blockchain"],
                "style": "Fast and dynamic",
                "color_scheme": "Purple and teal gradients",
                "focus": "Speed and performance",
                "mood": "Energetic and modern"
            },
            "cardano": {
                "subject": "Cardano",
                "elements": ["Scientific approach", "proof of stake", "sustainability"],
                "style": "Academic and methodical",
                "color_scheme": "Blue and white tones",
                "focus": "Research-driven development",
                "mood": "Trustworthy and scientific"
            },
            "polkadot": {
                "subject": "Polkadot",
                "elements": ["Interoperability", "parachains", "cross-chain"],
                "style": "Connected and modular",
                "color_scheme": "Pink and purple tones",
                "focus": "Blockchain connectivity",
                "mood": "Collaborative and innovative"
            },
            "ripple": {
                "subject": "Ripple/XRP",
                "elements": ["Cross-border payments", "banking integration", "liquidity"],
                "style": "Professional and corporate",
                "color_scheme": "Blue and silver tones",
                "focus": "Financial infrastructure",
                "mood": "Professional and efficient"
            },
            "dogecoin": {
                "subject": "Dogecoin",
                "elements": ["Community-driven", "meme culture", "accessibility"],
                "style": "Fun and approachable",
                "color_scheme": "Gold and playful colors",
                "focus": "Community and adoption",
                "mood": "Lighthearted and accessible"
            },
            "defi": {
                "subject": "DeFi (Decentralized Finance)",
                "elements": ["Liquidity pools", "yield farming", "decentralized exchanges"],
                "style": "Interconnected and flowing",
                "color_scheme": "Green and blue gradients",
                "focus": "Financial freedom and innovation",
                "mood": "Revolutionary and empowering"
            },
            "nft": {
                "subject": "NFTs (Non-Fungible Tokens)",
                "elements": ["Digital art", "unique tokens", "collectibles"],
                "style": "Artistic and creative",
                "color_scheme": "Vibrant and diverse colors",
                "focus": "Digital ownership and creativity",
                "mood": "Creative and unique"
            },
            "regulation": {
                "subject": "Crypto Regulation",
                "elements": ["Government buildings", "legal documents", "compliance"],
                "style": "Formal and authoritative",
                "color_scheme": "Blue and gray professional tones",
                "focus": "Legal framework and compliance",
                "mood": "Serious and official"
            },
            "sec": {
                "subject": "SEC and Crypto Regulation",
                "elements": ["Government oversight", "legal framework", "compliance"],
                "style": "Formal and institutional",
                "color_scheme": "Navy blue and white",
                "focus": "Regulatory compliance",
                "mood": "Authoritative and serious"
            },
            "etf": {
                "subject": "Crypto ETF",
                "elements": ["Traditional finance", "institutional investment", "market access"],
                "style": "Professional and institutional",
                "color_scheme": "Blue and gold corporate colors",
                "focus": "Institutional adoption",
                "mood": "Professional and mainstream"
            },
            "mining": {
                "subject": "Crypto Mining",
                "elements": ["Mining rigs", "computational power", "energy"],
                "style": "Industrial and powerful",
                "color_scheme": "Dark with electric blue accents",
                "focus": "Computational infrastructure",
                "mood": "Powerful and industrial"
            },
            "stablecoin": {
                "subject": "Stablecoins",
                "elements": ["Price stability", "fiat backing", "reliable value"],
                "style": "Stable and balanced",
                "color_scheme": "Green and white clean tones",
                "focus": "Stability and reliability",
                "mood": "Trustworthy and stable"
            },
            "airdrop": {
                "subject": "Crypto Airdrop",
                "elements": ["Token distribution", "rewards", "community incentives"],
                "style": "Generous and exciting",
                "color_scheme": "Gold and bright colors",
                "focus": "Community rewards and distribution",
                "mood": "Exciting and rewarding"
            },
            "trading": {
                "subject": "Crypto Trading",
                "elements": ["Charts", "candlesticks", "market analysis"],
                "style": "Dynamic and analytical",
                "color_scheme": "Green and red with dark background",
                "focus": "Market movements and analysis",
                "mood": "Dynamic and analytical"
            },
            "market": {
                "subject": "Crypto Market",
                "elements": ["Price charts", "market trends", "global economy"],
                "style": "Data-driven and global",
                "color_scheme": "Blue and green financial colors",
                "focus": "Market trends and economics",
                "mood": "Analytical and global"
            },
            "web3": {
                "subject": "Web3",
                "elements": ["Decentralization", "user ownership", "new internet"],
                "style": "Futuristic and decentralized",
                "color_scheme": "Cyan and purple tech colors",
                "focus": "Decentralized internet",
                "mood": "Revolutionary and futuristic"
            },
            "metaverse": {
                "subject": "Metaverse",
                "elements": ["Virtual worlds", "digital avatars", "immersive experiences"],
                "style": "Immersive and 3D",
                "color_scheme": "Neon and vibrant digital colors",
                "focus": "Virtual reality and digital spaces",
                "mood": "Futuristic and immersive"
            }
        }
        
        # Encontrar contexto mais específico
        for keyword, context in crypto_projects.items():
            if keyword in text:
                # Adicionar descrição contextual baseada no título
                context["description"] = f"News article about {context['subject']}: {title[:100]}"
                return context
        
        # Contexto genérico para criptomoedas (fallback)
        return {
            "subject": "Cryptocurrency Market",
            "description": f"General cryptocurrency news: {title[:100]}",
            "elements": ["Digital currencies", "blockchain technology", "crypto market"],
            "style": "Modern and professional",
            "color_scheme": "Blue and orange crypto colors",
            "focus": "Cryptocurrency and blockchain innovation",
            "mood": "Professional and informative"
        }
    
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

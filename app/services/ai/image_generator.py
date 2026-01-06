from openai import OpenAI
import cloudinary
import cloudinary.uploader
import requests
from app.core.config import settings
from app.core.logging import logger

# Configurar Cloudinary
cloudinary.config(
    cloud_name=settings.CLOUDINARY_CLOUD_NAME,
    api_key=settings.CLOUDINARY_API_KEY,
    api_secret=settings.CLOUDINARY_API_SECRET
)

class ImageGenerator:
    def __init__(self):
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
    
    def _extract_detailed_context(self, title: str, content: str) -> dict:
        """
        Extrai contexto detalhado do artigo para gerar prompt específico.
        Analisa título e conteúdo para identificar o tema principal.
        """
        text = f"{title} {content[:500]}".lower()
        
        # Contextos específicos por tema/projeto
        crypto_projects = {
            "ethereum": {
                "subject": "Ethereum blockchain technology",
                "scene": "Modern data center with glowing purple and blue server racks, holographic smart contract interfaces floating in the air",
                "style": "Photorealistic, cinematic lighting, high-tech atmosphere",
                "avoid": "Bitcoin symbols, BTC logos, orange coins",
                "mood": "Innovative and cutting-edge"
            },
            "solana": {
                "subject": "Solana high-speed blockchain",
                "scene": "Futuristic network visualization with purple and teal light streams flowing at high speed through fiber optic cables",
                "style": "Photorealistic, motion blur effects, dynamic energy",
                "avoid": "Bitcoin symbols, BTC logos, static imagery",
                "mood": "Fast-paced and energetic"
            },
            "cardano": {
                "subject": "Cardano blockchain research",
                "scene": "Clean modern laboratory with scientists analyzing blockchain data on transparent holographic displays, blue ambient lighting",
                "style": "Photorealistic, professional scientific setting",
                "avoid": "Bitcoin symbols, BTC logos, casual imagery",
                "mood": "Scientific and trustworthy"
            },
            "polkadot": {
                "subject": "Polkadot interoperability network",
                "scene": "Multiple interconnected blockchain networks visualized as glowing pink and purple nodes connecting through space",
                "style": "Photorealistic, cosmic background, interconnected web",
                "avoid": "Bitcoin symbols, BTC logos, single chain imagery",
                "mood": "Collaborative and interconnected"
            },
            "ripple": {
                "subject": "Ripple cross-border payment system",
                "scene": "Modern banking headquarters with digital payment streams flowing across world map hologram, blue and silver tones",
                "style": "Photorealistic, corporate professional, global scale",
                "avoid": "Bitcoin symbols, BTC logos, casual crypto imagery",
                "mood": "Professional and efficient"
            },
            "xrp": {
                "subject": "XRP digital payment network",
                "scene": "International financial district at night with digital payment networks illuminated across skyscrapers",
                "style": "Photorealistic, urban cityscape, blue lighting",
                "avoid": "Bitcoin symbols, BTC logos",
                "mood": "Global and institutional"
            },
            "dogecoin": {
                "subject": "Dogecoin community cryptocurrency",
                "scene": "Vibrant community gathering with digital gold coins floating, warm friendly atmosphere, diverse group of people",
                "style": "Photorealistic, warm lighting, community-focused",
                "avoid": "Bitcoin symbols, BTC logos, serious corporate imagery",
                "mood": "Friendly and accessible"
            },
            "shiba": {
                "subject": "Shiba Inu token ecosystem",
                "scene": "Dynamic cryptocurrency trading floor with energetic traders, gold and red accent lighting",
                "style": "Photorealistic, high energy, modern trading environment",
                "avoid": "Bitcoin symbols, BTC logos",
                "mood": "Energetic and community-driven"
            },
            "defi": {
                "subject": "Decentralized finance ecosystem",
                "scene": "Futuristic financial hub with floating holographic liquidity pools, green and blue data streams, people interacting with DeFi protocols",
                "style": "Photorealistic, high-tech financial setting",
                "avoid": "Bitcoin symbols, BTC logos, traditional banking imagery",
                "mood": "Revolutionary and empowering"
            },
            "nft": {
                "subject": "NFT digital art marketplace",
                "scene": "Modern art gallery showcasing digital artworks on holographic displays, diverse colorful art pieces, collectors viewing",
                "style": "Photorealistic, gallery lighting, artistic atmosphere",
                "avoid": "Bitcoin symbols, BTC logos, generic crypto imagery",
                "mood": "Creative and artistic"
            },
            "stablecoin": {
                "subject": "Stablecoin digital currency",
                "scene": "Secure vault with physical gold bars alongside digital currency displays, balanced scales symbolizing stability",
                "style": "Photorealistic, secure banking environment, professional",
                "avoid": "Bitcoin symbols, BTC logos, volatile imagery",
                "mood": "Stable and trustworthy"
            },
            "airdrop": {
                "subject": "Cryptocurrency airdrop distribution",
                "scene": "Excited people receiving glowing digital tokens falling from above like golden rain, celebration atmosphere",
                "style": "Photorealistic, celebratory lighting, dynamic motion",
                "avoid": "Bitcoin symbols, BTC logos exclusively",
                "mood": "Exciting and rewarding"
            },
            "sec": {
                "subject": "SEC cryptocurrency regulation",
                "scene": "Professional government office with officials reviewing digital asset documents, American flag, serious atmosphere",
                "style": "Photorealistic, official government setting, formal",
                "avoid": "Bitcoin symbols, BTC logos, casual imagery",
                "mood": "Authoritative and serious"
            },
            "regulação": {
                "subject": "Cryptocurrency regulation and compliance",
                "scene": "Modern government building with lawmakers discussing cryptocurrency policy, legal documents, formal setting",
                "style": "Photorealistic, professional governmental atmosphere",
                "avoid": "Bitcoin symbols, BTC logos, informal imagery",
                "mood": "Official and serious"
            },
            "etf": {
                "subject": "Cryptocurrency ETF investment",
                "scene": "Wall Street trading floor with cryptocurrency ETF data on multiple screens, professional traders, corporate setting",
                "style": "Photorealistic, financial district, professional",
                "avoid": "Bitcoin symbols exclusively, focus on institutional finance",
                "mood": "Professional and mainstream"
            },
            "mining": {
                "subject": "Cryptocurrency mining operation",
                "scene": "Large industrial mining facility with rows of ASIC miners, cooling systems, blue LED lights, technical workers monitoring",
                "style": "Photorealistic, industrial setting, technical atmosphere",
                "avoid": "Bitcoin symbols exclusively, show mining hardware",
                "mood": "Industrial and powerful"
            },
            "trading": {
                "subject": "Cryptocurrency trading",
                "scene": "Modern trading desk with multiple monitors showing candlestick charts, professional trader analyzing markets",
                "style": "Photorealistic, trading floor atmosphere, dynamic",
                "avoid": "Bitcoin symbols exclusively, show diverse crypto charts",
                "mood": "Analytical and professional"
            },
            "web3": {
                "subject": "Web3 decentralized internet",
                "scene": "Futuristic digital landscape with interconnected nodes, users controlling their own data, cyan and purple lighting",
                "style": "Photorealistic, high-tech digital world",
                "avoid": "Bitcoin symbols, BTC logos, Web2 imagery",
                "mood": "Revolutionary and user-empowered"
            },
            "metaverse": {
                "subject": "Metaverse virtual world",
                "scene": "Immersive virtual reality environment with avatars interacting, neon-lit digital cities, VR headsets",
                "style": "Photorealistic, futuristic virtual world, vibrant",
                "avoid": "Bitcoin symbols, BTC logos, flat 2D imagery",
                "mood": "Futuristic and immersive"
            },
            "bitcoin": {
                "subject": "Bitcoin digital currency",
                "scene": "Secure digital vault with glowing golden Bitcoin represented as pure energy or light (not physical coins), blockchain network visualization",
                "style": "Photorealistic, golden warm lighting, secure atmosphere",
                "avoid": "Physical Bitcoin coins with B symbol, generic crypto imagery",
                "mood": "Valuable and established"
            }
        }
        
        # Detectar tema principal
        for keyword, context in crypto_projects.items():
            if keyword in text:
                logger.info(f"Detected subject: {keyword}")
                return context
        
        # Contexto padrão genérico (evita Bitcoin)
        logger.info("Using default generic crypto context")
        return {
            "subject": "Cryptocurrency and blockchain technology",
            "scene": "Modern financial technology hub with diverse digital assets represented as flowing light streams, holographic data displays",
            "style": "Photorealistic, professional tech atmosphere, balanced lighting",
            "avoid": "Bitcoin symbols, BTC logos, single crypto focus",
            "mood": "Professional and diverse"
        }
    
    def _build_realistic_prompt(self, title: str, content: str) -> str:
        """
        Constrói prompt detalhado e realista baseado no contexto do artigo.
        """
        context = self._extract_detailed_context(title, content)
        
        prompt = f"""Create a photorealistic, professional image for a cryptocurrency news article.

Article title: {title[:100]}

SCENE DESCRIPTION:
{context['scene']}

VISUAL STYLE:
{context['style']}
- Cinematic composition with depth of field
- Professional photography quality
- Realistic lighting and shadows
- High detail and texture
- Modern and clean aesthetic

IMPORTANT RESTRICTIONS:
- MUST AVOID: {context['avoid']}
- NO text overlays or captions
- NO brand logos or trademarks
- NO specific people's faces (use anonymous figures if needed)
- NO cryptocurrency symbols or logos as main focus
- Focus on the scene and atmosphere, not symbols

TECHNICAL SPECS:
- Photorealistic rendering
- Landscape orientation (16:9 ratio)
- High contrast for web readability
- Professional color grading

MOOD: {context['mood']}

The image should feel like a professional stock photo for financial/tech journalism, not abstract crypto art."""

        logger.info(f"Generated realistic prompt for subject: {context['subject']}")
        return prompt
    
    async def generate_and_upload_image(self, title: str, content: str) -> str:
        """
        Gera imagem usando DALL-E 3 e faz upload para Cloudinary.
        
        Args:
            title: Título do artigo
            content: Conteúdo do artigo
            
        Returns:
            URL da imagem no Cloudinary
        """
        try:
            logger.info(f"Gerando imagem para: {title[:50]}...")
            
            # Gerar prompt realista
            prompt = self._build_realistic_prompt(title, content)
            
            # Gerar imagem com DALL-E 3
            response = self.client.images.generate(
                model="dall-e-3",
                prompt=prompt,
                size="1792x1024",  # Landscape format
                quality="standard",
                n=1,
            )
            
            image_url = response.data[0].url
            logger.info(f"Imagem gerada: {image_url}")
            
            # Fazer upload para Cloudinary
            upload_response = cloudinary.uploader.upload(
                image_url,
                folder="vivacripto/posts",
                format="webp",
                quality="auto:good",
                fetch_format="auto"
            )
            
            cloudinary_url = upload_response['secure_url']
            logger.info(f"Imagem enviada: {cloudinary_url}")
            
            return cloudinary_url
            
        except Exception as e:
            logger.error(f"Erro ao gerar imagem: {str(e)}")
            raise

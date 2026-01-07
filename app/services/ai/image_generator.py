"""
Image Generation Service - Premium Editorial Style
Gera imagens premium para artigos seguindo estilo Financial Times/Bloomberg
"""
from typing import Optional
from openai import OpenAI
import cloudinary
import cloudinary.uploader
from app.core.config import settings
from app.core.logging import logger


class ImageGenerator:
    """Gerador de imagens premium por categoria"""
    
    # Prompts premium por categoria - Estilo Financial Times/Bloomberg
    CATEGORY_PROMPTS = {
        "bitcoin": {
            "prompt": "A highly detailed, premium physical Bitcoin coin made of matte black metal with brushed gold accents and glowing orange circuit traces. The coin rests on a dark, polished obsidian surface reflecting subtle green financial candlestick charts in the background. Dramatic cinematic lighting, professional editorial photography style, shallow depth of field, 8k render.",
            "colors": "orange, gold, black",
            "mood": "solid, premium, valuable"
        },
        "ethereum": {
            "prompt": "A futuristic, glowing blue and purple crystal Ethereum diamond logo hovering at the center of a complex, interconnected digital network structure. Glowing lines connect abstract geometric nodes and transparent blocks representing smart contracts. High-tech 3D concept art, clean composition, volumetric fog, octane render, 8k resolution.",
            "colors": "blue, purple, cyan",
            "mood": "technological, networked, innovative"
        },
        "altcoins": {
            "prompt": "An isometric 3D render view of a diverse digital blockchain ecosystem. Various abstract, glowing data blocks in cyan, magenta, and orange colors connected by light streams, forming a futuristic infrastructure city. Clean tech illustration style, highly detailed, dark background, modern aesthetic, 8k.",
            "colors": "cyan, magenta, orange",
            "mood": "diverse, ecosystem, interconnected"
        },
        "defi": {
            "prompt": "Abstract visualization of decentralized finance (DeFi). Glowing golden and blue liquid light flowing between transparent, interlocking digital gears and abstract liquidity pools. Futuristic financial concept art, clean rendering, sense of motion, no central bank imagery, 8k.",
            "colors": "gold, blue, cyan",
            "mood": "liquid, flowing, decentralized"
        },
        "regulacao": {
            "prompt": "A minimalist 3D render of a stylized glass justice gavel resting on a digital ledger tablet with subtle blockchain patterns. Blurred background of a modern government building façade with faint data circuits. Serious tone, muted blue and grey professional lighting, editorial style, 8k.",
            "colors": "blue, grey, silver",
            "mood": "serious, legal, institutional"
        },
        "airdrop": {
            "prompt": "Stylized digital illustration of glowing futuristic loot crates attached to digital data-parachutes, descending from a cloud network onto a glowing abstract map. Vibrant, energetic lighting, high-quality 3D render, sense of reward, 8k.",
            "colors": "vibrant, multi-color, energetic",
            "mood": "rewarding, community, exciting"
        }
    }
    
    # Negative prompt universal
    NEGATIVE_PROMPT = "text, letters, watermark, blurry, low resolution, cartoon, ugly, deformed, messy, crowded, cheap neon, logos, symbols, typography"
    
    def __init__(self):
        """Inicializa o gerador de imagens"""
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        
        # Configurar Cloudinary
        cloudinary.config(
            cloud_name=settings.CLOUDINARY_CLOUD_NAME,
            api_key=settings.CLOUDINARY_API_KEY,
            api_secret=settings.CLOUDINARY_API_SECRET
        )
    
    def _get_category_slug(self, category_name: Optional[str]) -> str:
        """
        Converte nome de categoria para slug
        
        Args:
            category_name: Nome da categoria (ex: "Bitcoin", "Regulação")
            
        Returns:
            Slug da categoria (ex: "bitcoin", "regulacao")
        """
        if not category_name:
            return "bitcoin"  # Default
        
        # Normalizar para minúsculas e remover acentos
        slug = category_name.lower()
        slug = slug.replace("ç", "c").replace("ã", "a").replace("õ", "o")
        
        # Mapear variações comuns
        if "regula" in slug or "sec" in slug or "lei" in slug or "governo" in slug:
            return "regulacao"
        elif "eth" in slug:
            return "ethereum"
        elif "btc" in slug or "bitcoin" in slug:
            return "bitcoin"
        elif "defi" in slug or "descentraliz" in slug:
            return "defi"
        elif "airdrop" in slug:
            return "airdrop"
        elif "alt" in slug or "moeda" in slug:
            return "altcoins"
        
        return "bitcoin"  # Default fallback
    
    def _extract_keywords(self, title: str, content: str) -> str:
        """
        Extrai palavras-chave relevantes do título e conteúdo
        
        Args:
            title: Título do artigo
            content: Conteúdo do artigo
            
        Returns:
            String com palavras-chave principais
        """
        # Palavras-chave relevantes para cripto
        relevant_terms = [
            "price surge", "market crash", "adoption", "regulation",
            "innovation", "partnership", "launch", "upgrade",
            "security breach", "institutional investment", "ETF",
            "halving", "staking", "mining", "trading volume",
            "all-time high", "bear market", "bull run"
        ]
        
        text = (title + " " + content[:500]).lower()
        
        # Encontrar termos relevantes
        found_terms = [term for term in relevant_terms if term in text]
        
        if found_terms:
            return ", ".join(found_terms[:2])  # Máximo 2 termos
        
        # Fallback: pegar primeiras palavras significativas do título
        words = title.split()[:3]
        return " ".join(words) if words else ""
    
    async def generate_and_upload_image(
        self,
        title: str,
        content: str,
        category_name: Optional[str] = None
    ) -> str:
        """
        Gera imagem premium contextual e faz upload para Cloudinary
        
        Args:
            title: Título do artigo
            content: Conteúdo do artigo
            category_name: Nome da categoria do artigo
            
        Returns:
            URL da imagem no Cloudinary
        """
        try:
            logger.info(f"Gerando imagem premium para: {title[:50]}...")
            
            # Determinar categoria
            category_slug = self._get_category_slug(category_name)
            category_config = self.CATEGORY_PROMPTS.get(
                category_slug,
                self.CATEGORY_PROMPTS["bitcoin"]  # Fallback
            )
            
            # Usar prompt premium da categoria
            base_prompt = category_config["prompt"]
            
            # Adicionar contexto do artigo ao prompt (sutilmente)
            keywords = self._extract_keywords(title, content)
            context_hint = f" The scene subtly reflects the theme of: {keywords}." if keywords else ""
            
            final_prompt = base_prompt + context_hint
            
            logger.info(f"Image prompt - Category: {category_slug}, Theme: {keywords if keywords else 'default'}")
            
            # Gerar imagem com DALL-E 3
            response = self.client.images.generate(
                model="dall-e-3",
                prompt=final_prompt,
                size="1792x1024",  # 16:9 aspect ratio
                quality="hd",
                n=1,
            )
            
            image_url = response.data[0].url
            logger.info(f"Imagem gerada: {image_url}")
            
            # Upload para Cloudinary
            upload_result = cloudinary.uploader.upload(
                image_url,
                folder="vivacripto/posts",
                format="webp",
                quality="auto:best",
                fetch_format="auto"
            )
            
            cloudinary_url = upload_result["secure_url"]
            logger.info(f"Imagem enviada: {cloudinary_url}")
            
            return cloudinary_url
            
        except Exception as e:
            logger.error(f"Erro ao gerar/enviar imagem: {type(e).__name__}: {e}")
            raise

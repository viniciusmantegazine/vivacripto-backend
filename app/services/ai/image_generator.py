"""
Image Generation Service - Contextual Editorial Style
Gera imagens contextualizadas para artigos seguindo estilo jornalístico editorial
"""
from typing import Optional, Dict
from openai import OpenAI
import cloudinary
import cloudinary.uploader
from app.core.config import settings
from app.core.logging import logger
import re


class ImageGenerator:
    """Gerador de imagens contextualizadas por categoria"""
    
    # Configurações base por categoria
    CATEGORY_CONFIGS = {
        "bitcoin": {
            "base_context": "Bitcoin as a consolidated financial asset",
            "environment": "traditional financial market environment, trading floor, or modern financial institution",
            "visual_style": "professional financial photography, clean composition",
            "avoid": "floating coins, excessive futurism, neon lights, sci-fi elements"
        },
        "ethereum": {
            "base_context": "Ethereum blockchain technology and smart contracts",
            "environment": "clean technological infrastructure, modern data center, or innovation lab",
            "visual_style": "tech editorial photography, focus on scalability and innovation",
            "avoid": "glowing crystals, excessive holographic effects, cyberpunk aesthetics"
        },
        "altcoins": {
            "base_context": "Alternative cryptocurrency ecosystem and blockchain diversity",
            "environment": "diverse technological landscape, innovation hub, or digital infrastructure",
            "visual_style": "modern tech illustration, clean and organized",
            "avoid": "random floating coins, chaotic compositions, generic crypto symbols"
        },
        "defi": {
            "base_context": "Decentralized finance protocols and financial innovation",
            "environment": "modern fintech environment, digital banking interface, or financial technology lab",
            "visual_style": "clean financial tech visualization, professional and trustworthy",
            "avoid": "excessive glowing effects, liquid gold, abstract chaos"
        },
        "regulacao": {
            "base_context": "Cryptocurrency regulation and government policy",
            "environment": "institutional setting: parliament, congress, government building, or official meeting room",
            "visual_style": "serious editorial photography, documentary style, credible and institutional",
            "avoid": "blockchain symbols, digital patterns, tech elements, futuristic aesthetics"
        },
        "airdrop": {
            "base_context": "Token distribution and community rewards",
            "environment": "community event, digital distribution platform, or reward system interface",
            "visual_style": "vibrant but professional, sense of reward and community",
            "avoid": "parachutes with coins, excessive gamification, childish illustrations"
        }
    }
    
    # Negative prompt universal - mais restritivo
    BASE_NEGATIVE_PROMPT = """
    text, letters, watermark, logos, typography, brand names,
    blurry, low resolution, poor quality, amateur photography,
    cartoon style, anime, manga, comic book art,
    ugly, deformed, distorted, messy composition, cluttered,
    cheap neon lights, excessive lens flare, over-saturated colors
    """
    
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
        if "regula" in slug or "sec" in slug or "lei" in slug or "governo" in slug or "senado" in slug or "congresso" in slug:
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
    
    def _extract_main_theme(self, title: str, content: str) -> str:
        """
        Extrai o tema principal da notícia para contextualização
        
        Args:
            title: Título do artigo
            content: Conteúdo do artigo (primeiros parágrafos)
            
        Returns:
            Descrição do tema principal em inglês
        """
        # Combinar título e início do conteúdo
        text = f"{title} {content[:300]}".lower()
        
        # Dicionário de temas e suas palavras-chave
        theme_keywords = {
            "price surge and market rally": ["sobe", "alta", "dispara", "valoriza", "recorde", "máxima histórica", "all-time high", "surge", "rally"],
            "market crash and price decline": ["cai", "queda", "desvaloriza", "crash", "bear market", "correção"],
            "government regulation and policy": ["governo", "regulação", "lei", "senado", "congresso", "sec", "cvm", "política", "regulamenta"],
            "institutional adoption": ["instituição", "empresa", "adoção", "corporação", "wall street", "banco"],
            "technological upgrade": ["atualização", "upgrade", "melhoria", "tecnologia", "protocolo", "rede"],
            "security breach or hack": ["hack", "ataque", "vulnerabilidade", "segurança", "roubo"],
            "partnership announcement": ["parceria", "acordo", "colaboração", "aliança"],
            "product launch": ["lança", "lançamento", "novo produto", "estreia"],
            "ETF approval": ["etf", "fundo", "aprovação", "sec"],
            "mining and halving": ["mineração", "halving", "recompensa", "bloco"],
            "legal proceedings": ["processo", "judicial", "tribunal", "justiça", "ação legal"]
        }
        
        # Encontrar tema mais relevante
        for theme, keywords in theme_keywords.items():
            if any(keyword in text for keyword in keywords):
                return theme
        
        # Fallback: extrair primeiras palavras significativas do título
        # Remover palavras comuns
        stop_words = ["o", "a", "de", "do", "da", "em", "para", "com", "por", "the", "and", "of", "to"]
        words = [w for w in title.lower().split() if w not in stop_words and len(w) > 3]
        
        if words:
            return " ".join(words[:4])
        
        return "cryptocurrency market development"
    
    def _should_include_crypto_symbols(self, category: str, title: str, content: str) -> bool:
        """
        Determina se símbolos de criptomoedas devem aparecer na imagem
        
        Args:
            category: Categoria do artigo
            title: Título do artigo
            content: Conteúdo do artigo
            
        Returns:
            True se símbolos cripto são relevantes, False caso contrário
        """
        text = f"{title} {content[:200]}".lower()
        
        # Categorias que raramente precisam de símbolos cripto
        if category == "regulacao":
            # Apenas se mencionar explicitamente Bitcoin/crypto no título
            return "bitcoin" in title.lower() or "btc" in title.lower() or "criptomoeda" in title.lower()
        
        # Categorias que sempre podem ter símbolos
        if category in ["bitcoin", "ethereum"]:
            return True
        
        # Para outras categorias, verificar relevância
        crypto_mentions = ["bitcoin", "btc", "ethereum", "eth", "coin", "token", "crypto"]
        mention_count = sum(1 for term in crypto_mentions if term in text)
        
        return mention_count >= 2  # Precisa mencionar pelo menos 2 vezes
    
    def _build_contextual_prompt(
        self,
        title: str,
        content: str,
        category_slug: str
    ) -> str:
        """
        Constrói prompt contextualizado dinamicamente
        
        Args:
            title: Título do artigo
            content: Conteúdo do artigo
            category_slug: Slug da categoria
            
        Returns:
            Prompt completo para DALL-E 3
        """
        config = self.CATEGORY_CONFIGS.get(category_slug, self.CATEGORY_CONFIGS["bitcoin"])
        
        # Extrair tema principal
        main_theme = self._extract_main_theme(title, content)
        
        # Verificar se deve incluir símbolos cripto
        include_symbols = self._should_include_crypto_symbols(category_slug, title, content)
        
        # Construir prompt base
        prompt_parts = [
            "Editorial photograph for a professional cryptocurrency news portal.",
            f"\nNews context: {main_theme}",
            f"\nCategory: {config['base_context']}",
            f"\nSetting: {config['environment']}",
            "\nRealistic scene directly representing the news theme.",
            "Environment coherent with the context (institutional, political, technological, or urban).",
            f"\nVisual style: {config['visual_style']}",
            "Clean composition, focus on visual clarity and credibility.",
            "Professional lighting, balanced colors, high editorial quality.",
        ]
        
        # Adicionar instrução sobre símbolos cripto
        if not include_symbols:
            prompt_parts.append("\nIMPORTANT: Avoid generic cryptocurrency symbols (Bitcoin logo, coins, blockchain graphics) as they are not relevant to this specific news theme.")
        elif category_slug == "bitcoin":
            prompt_parts.append("\nBitcoin may appear as a physical coin or financial chart element, but avoid excessive futuristic styling.")
        
        # Adicionar restrições específicas da categoria
        prompt_parts.append(f"\nAvoid: {config['avoid']}")
        
        return " ".join(prompt_parts)
    
    def _build_negative_prompt(self, category_slug: str) -> str:
        """
        Constrói negative prompt específico por categoria
        
        Args:
            category_slug: Slug da categoria
            
        Returns:
            Negative prompt completo
        """
        category_specific = {
            "regulacao": ", Bitcoin symbols, blockchain graphics, digital patterns, holographic effects, futuristic elements, sci-fi aesthetics, neon lights",
            "bitcoin": ", excessive glowing effects, floating coins, cyberpunk style, neon colors, sci-fi elements",
            "ethereum": ", glowing crystals, excessive holographic effects, cyberpunk aesthetics, floating geometric shapes",
            "defi": ", liquid gold, excessive glowing, abstract chaos, random floating elements",
            "altcoins": ", random floating coins, chaotic composition, generic crypto symbols everywhere",
            "airdrop": ", parachutes with coins, excessive gamification, childish cartoon style"
        }
        
        specific = category_specific.get(category_slug, "")
        return self.BASE_NEGATIVE_PROMPT + specific
    
    async def generate_and_upload_image(
        self,
        title: str,
        content: str,
        category_name: Optional[str] = None
    ) -> str:
        """
        Gera imagem contextualizada e faz upload para Cloudinary
        
        Args:
            title: Título do artigo
            content: Conteúdo do artigo
            category_name: Nome da categoria do artigo
            
        Returns:
            URL da imagem no Cloudinary
        """
        try:
            logger.info(f"Gerando imagem contextualizada para: {title[:50]}...")
            
            # Determinar categoria
            category_slug = self._get_category_slug(category_name)
            
            # Construir prompt contextualizado
            final_prompt = self._build_contextual_prompt(title, content, category_slug)
            
            # Construir negative prompt
            negative_prompt = self._build_negative_prompt(category_slug)
            
            # Extrair tema para log
            theme = self._extract_main_theme(title, content)
            
            logger.info(f"Image generation - Category: {category_slug}, Theme: {theme}")
            logger.debug(f"Full prompt: {final_prompt[:200]}...")
            
            # Gerar imagem com DALL-E 3
            # Nota: DALL-E 3 não suporta negative_prompt diretamente,
            # mas incluímos as restrições no prompt principal
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
            logger.info(f"Imagem enviada para Cloudinary: {cloudinary_url}")
            
            return cloudinary_url
            
        except Exception as e:
            logger.error(f"Erro ao gerar/enviar imagem: {type(e).__name__}: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise

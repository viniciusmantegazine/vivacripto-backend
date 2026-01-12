"""
Image Generation Service - Contextual Editorial Style v2.0
Gera imagens contextualizadas para artigos seguindo estilo jornalístico editorial
Com sistema de extração de entidades e construção dinâmica de prompts
"""
from typing import Optional, Dict, List
from openai import OpenAI
import cloudinary
import cloudinary.uploader
from app.core.config import settings
from app.core.logging import logger
import re


class ImageGenerator:
    """Gerador de imagens contextualizadas v2.0 - com análise semântica de entidades"""
    
    # Configurações base por categoria (mantidas como fallback)
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
    
    # Dicionário de entidades conhecidas (expandir conforme necessário)
    KNOWN_ENTITIES = {
        "companies": {
            "Coinbase": ["coinbase"],
            "Bank of America": ["bank of america", "bofa"],
            "BlackRock": ["blackrock"],
            "MicroStrategy": ["microstrategy"],
            "Tesla": ["tesla"],
            "Binance": ["binance"],
            "Kraken": ["kraken"],
            "Ripple": ["ripple"],
            "Circle": ["circle"],
            "Gemini": ["gemini"],
            "PayPal": ["paypal"],
            "Visa": ["visa"],
            "Mastercard": ["mastercard"],
            "JPMorgan": ["jpmorgan", "jp morgan"],
            "Goldman Sachs": ["goldman sachs"],
            "Morgan Stanley": ["morgan stanley"],
            "Fidelity": ["fidelity"],
            "Grayscale": ["grayscale"],
            "Tether": ["tether"],
        },
        "people": {
            "Gary Gensler": ["gary gensler", "gensler"],
            "Michael Saylor": ["michael saylor", "saylor"],
            "Vitalik Buterin": ["vitalik", "buterin"],
            "Changpeng Zhao": ["changpeng zhao", "cz", "zhao"],
            "Sam Bankman-Fried": ["sam bankman", "sbf"],
            "Brian Armstrong": ["brian armstrong"],
            "Cathie Wood": ["cathie wood"],
        },
        "protocols": {
            "Bitcoin": ["bitcoin", "btc"],
            "Ethereum": ["ethereum", "eth"],
            "Solana": ["solana", "sol"],
            "Cardano": ["cardano", "ada"],
            "Ripple": ["xrp"],
            "Polygon": ["polygon", "matic"],
            "Avalanche": ["avalanche", "avax"],
            "Polkadot": ["polkadot", "dot"],
        },
        "institutions": {
            "SEC": ["sec", "securities and exchange commission"],
            "CFTC": ["cftc"],
            "Federal Reserve": ["federal reserve", "fed"],
            "Senado": ["senado", "senate"],
            "Congresso": ["congresso", "congress"],
            "CVM": ["cvm"],
            "Banco Central": ["banco central", "bacen"],
        }
    }
    
    # Negative prompt universal v2.0 - mais específico
    BASE_NEGATIVE_PROMPT = """text, letters, words, typography, watermark, signature, brand names,
blurry, low resolution, poor quality, amateur photography, out of focus,
cartoon, anime, manga, 3d render, illustration, painting,
ugly, deformed, distorted, disfigured, bad anatomy,
messy composition, cluttered, chaotic, unbalanced,
floating coins, glowing circuit lines, neon lights, cyberpunk style,
holographic displays, futuristic interfaces, sci-fi elements,
abstract geometric shapes, excessive lens flare, over-saturated colors,
cheap stock photo aesthetic"""
    
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
    
    def extract_entities(self, title: str, content: str) -> Dict[str, List[str]]:
        """
        Extrai entidades nomeadas do título e conteúdo (v2.0)
        
        Args:
            title: Título do artigo
            content: Conteúdo do artigo
            
        Returns:
            Dict com categorias de entidades: {
                "companies": ["Coinbase", "Bank of America"],
                "people": ["Gary Gensler"],
                "protocols": ["Ethereum"],
                "institutions": ["SEC"]
            }
        """
        text = f"{title.lower()} {content[:500].lower()}"
        
        entities = {
            "companies": [],
            "people": [],
            "protocols": [],
            "institutions": []
        }
        
        # Buscar entidades no texto
        for category, entity_dict in self.KNOWN_ENTITIES.items():
            for entity_name, keywords in entity_dict.items():
                if any(keyword in text for keyword in keywords):
                    entities[category].append(entity_name)
        
        logger.debug(f"Entidades extraídas: {entities}")
        return entities
    
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
            "corporate financial analysis": ["recomendação", "rating", "análise", "avaliação", "upgrade", "downgrade", "buy", "sell"],
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
        stop_words = ["o", "a", "de", "do", "da", "em", "para", "com", "por", "the", "and", "of", "to"]
        words = [w for w in title.lower().split() if w not in stop_words and len(w) > 3]
        
        if words:
            return " ".join(words[:4])
        
        return "cryptocurrency market development"
    
    def determine_visual_context(
        self, 
        entities: Dict[str, List[str]], 
        category: str,
        theme: str
    ) -> Dict[str, str]:
        """
        Determina o contexto visual baseado nas entidades e categoria (v2.0)
        
        Args:
            entities: Dict com entidades extraídas
            category: Categoria do artigo
            theme: Tema principal da notícia
            
        Returns:
            Dict com: {
                "scene": "Descrição do cenário",
                "elements": "Elementos visuais específicos",
                "crypto_symbols": "none" | "subtle" | "prominent"
            }
        """
        context = {
            "scene": "",
            "elements": "",
            "crypto_symbols": "none"
        }
        
        has_companies = len(entities["companies"]) > 0
        has_institutions = len(entities["institutions"]) > 0
        has_protocols = len(entities["protocols"]) > 0
        has_people = len(entities["people"]) > 0
        
        # Caso 1: Empresas + Empresas (ex: Bank of America + Coinbase)
        if len(entities["companies"]) >= 2:
            companies_str = " and ".join(entities["companies"][:2])
            context["scene"] = "A modern, clean corporate meeting room or financial analyst's office"
            context["elements"] = f"Subtle logos of {companies_str} on screens or documents. Two professionals in business attire analyzing data on sleek monitors."
            context["crypto_symbols"] = "none"
            logger.info(f"Visual context: Corporate (multiple companies) - {companies_str}")
        
        # Caso 2: Instituição + Protocolo (ex: SEC + Ethereum)
        elif has_institutions and has_protocols:
            institution = entities["institutions"][0]
            protocol = entities["protocols"][0]
            context["scene"] = f"An official {institution} building or hearing room with formal institutional setting"
            context["elements"] = f"{institution} emblem visible, officials in formal attire, documents mentioning {protocol} on a table"
            context["crypto_symbols"] = "subtle"
            logger.info(f"Visual context: Institutional regulation - {institution} + {protocol}")
        
        # Caso 3: Empresa + Protocolo (ex: Tesla + Bitcoin, Coinbase + Ethereum)
        elif has_companies and has_protocols:
            company = entities["companies"][0]
            protocol = entities["protocols"][0]
            context["scene"] = f"A {company} office or technology center with modern corporate environment"
            context["elements"] = f"{company} branding visible, digital interface showing {protocol} integration, professional tech setting"
            context["crypto_symbols"] = "subtle"
            logger.info(f"Visual context: Corporate + Crypto - {company} + {protocol}")
        
        # Caso 4: Apenas Protocolo (ex: análise de preço do Bitcoin)
        elif has_protocols and not has_companies and not has_institutions:
            protocol = entities["protocols"][0]
            context["scene"] = "An abstract financial chart or professional trading floor environment"
            context["elements"] = f"Candlestick charts, trend lines, financial data visualization with {protocol} as the central concept"
            context["crypto_symbols"] = "prominent"
            logger.info(f"Visual context: Pure crypto analysis - {protocol}")
        
        # Caso 5: Pessoa + Instituição (ex: Gary Gensler na SEC)
        elif has_people and has_institutions:
            person = entities["people"][0]
            institution = entities["institutions"][0]
            context["scene"] = f"A {institution} press conference or official meeting room"
            context["elements"] = f"{person} speaking at a podium with {institution} backdrop, formal institutional setting"
            context["crypto_symbols"] = "none"
            logger.info(f"Visual context: Person + Institution - {person} at {institution}")
        
        # Caso 6: Apenas Empresa (ex: análise sobre Coinbase)
        elif has_companies and not has_protocols:
            company = entities["companies"][0]
            context["scene"] = f"A {company} corporate headquarters or office environment"
            context["elements"] = f"{company} branding, corporate professionals, modern office setting with financial data"
            context["crypto_symbols"] = "subtle"
            logger.info(f"Visual context: Single company - {company}")
        
        # Fallback: usar categoria padrão
        else:
            context = self._get_default_category_context(category)
            logger.info(f"Visual context: Fallback to category default - {category}")
        
        return context
    
    def _get_default_category_context(self, category: str) -> Dict[str, str]:
        """
        Retorna contexto visual padrão baseado na categoria (fallback)
        
        Args:
            category: Slug da categoria
            
        Returns:
            Dict com scene, elements e crypto_symbols
        """
        config = self.CATEGORY_CONFIGS.get(category, self.CATEGORY_CONFIGS["bitcoin"])
        
        return {
            "scene": config["environment"],
            "elements": f"Professional setting representing {config['base_context']}",
            "crypto_symbols": "subtle" if category in ["bitcoin", "ethereum"] else "none"
        }
    
    def build_dalle_prompt_v2(
        self,
        entities: Dict[str, List[str]],
        visual_context: Dict[str, str],
        theme: str
    ) -> str:
        """
        Constrói o prompt final para DALL-E 3 (v2.0)
        
        Args:
            entities: Entidades extraídas
            visual_context: Contexto visual determinado
            theme: Tema principal da notícia
            
        Returns:
            Prompt completo para DALL-E 3
        """
        # Construir lista de entidades para o prompt
        entity_list = []
        if entities["companies"]:
            entity_list.extend(entities["companies"][:2])  # Máximo 2 empresas
        if entities["people"]:
            entity_list.extend(entities["people"][:1])  # Máximo 1 pessoa
        if entities["institutions"]:
            entity_list.extend(entities["institutions"][:1])  # Máximo 1 instituição
        
        entities_str = " and ".join(entity_list) if entity_list else "cryptocurrency market"
        
        # Construir instruções sobre símbolos cripto
        crypto_instruction = ""
        if visual_context["crypto_symbols"] == "none":
            crypto_instruction = "\n\n**CRITICAL: DO NOT include any cryptocurrency symbols, logos, or physical coins. This story is about corporate/institutional finance, not the cryptocurrency itself.**"
        elif visual_context["crypto_symbols"] == "subtle":
            crypto_instruction = "\n\nCryptocurrency symbols may appear subtly as small icons on screens or charts, but should not be the main focus."
        elif visual_context["crypto_symbols"] == "prominent":
            crypto_instruction = "\n\nCryptocurrency symbols can be prominent as they are central to the story, but avoid clichés like floating coins or excessive futurism."
        
        prompt = f"""Professional editorial photograph for a financial news article.

**Main Subject:** {entities_str}
**News Theme:** {theme}

**Scene & Composition:**
- Setting: {visual_context["scene"]}
- Key Elements: {visual_context["elements"]}
- Focal Point: The human and corporate elements should be the primary focus, creating a credible and grounded scene.

**Visual Style:**
- Style: Corporate editorial photography, similar to images in The Wall Street Journal, Bloomberg, or Financial Times.
- Color Palette: Professional and muted (blues, grays, whites). Avoid neon or overly saturated colors.
- Lighting: Natural daylight or soft studio lighting. Clean and well-lit.
- Composition: Balanced, uncluttered, with clear visual hierarchy.
{crypto_instruction}

**Avoid:**
- Floating coins or tokens
- Holographic or futuristic interfaces
- Neon lights or cyberpunk aesthetics
- Generic blockchain graphics
- Cluttered or chaotic compositions
- Any visible text, watermarks, or prominent logos"""
        
        return prompt
    
    async def generate_and_upload_image(
        self,
        title: str,
        content: str,
        category_name: Optional[str] = None
    ) -> str:
        """
        Gera imagem contextualizada e faz upload para Cloudinary (v2.0)
        
        Args:
            title: Título do artigo
            content: Conteúdo do artigo
            category_name: Nome da categoria do artigo
            
        Returns:
            URL da imagem no Cloudinary
        """
        try:
            logger.info(f"Gerando imagem contextualizada v2.0 para: {title[:50]}...")
            
            # Determinar categoria
            category_slug = self._get_category_slug(category_name)
            
            # NOVO: Extrair entidades
            entities = self.extract_entities(title, content)
            
            # NOVO: Extrair tema principal
            theme = self._extract_main_theme(title, content)
            
            # NOVO: Determinar contexto visual baseado em entidades
            visual_context = self.determine_visual_context(entities, category_slug, theme)
            
            # NOVO: Construir prompt dinâmico v2.0
            final_prompt = self.build_dalle_prompt_v2(entities, visual_context, theme)
            
            logger.info(f"Image generation v2.0 - Category: {category_slug}, Theme: {theme}")
            logger.info(f"Entities: {entities}")
            logger.info(f"Visual context: {visual_context}")
            logger.debug(f"Full prompt: {final_prompt[:300]}...")
            
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
            logger.info(f"Imagem enviada para Cloudinary: {cloudinary_url}")
            
            return cloudinary_url
            
        except Exception as e:
            logger.error(f"Erro ao gerar/enviar imagem: {type(e).__name__}: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise

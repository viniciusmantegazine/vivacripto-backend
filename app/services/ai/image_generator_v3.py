"""
Image Generation Service - Digital Art Style v3.0
Gera imagens no estilo CoinDesk/CoinPaper: arte digital abstrata com elementos gráficos modernos
"""
from typing import Optional, Dict, List
from openai import OpenAI
import cloudinary
import cloudinary.uploader
from app.core.config import settings
from app.core.logging import logger
import re


class ImageGenerator:
    """Gerador de imagens v3.0 - Estilo Digital Art (CoinDesk/CoinPaper)"""
    
    # Configurações de estilo visual por categoria
    CATEGORY_VISUAL_STYLES = {
        "bitcoin": {
            "primary_color": "golden yellow (#FFD700)",
            "secondary_color": "deep black (#000000)",
            "accent_color": "neon green (#00FF00)",
            "main_element": "Bitcoin coin with intense golden glow",
            "background": "black background with golden geometric network lines",
            "style": "digital art, high contrast, futuristic"
        },
        "ethereum": {
            "primary_color": "electric purple (#8B00FF)",
            "secondary_color": "deep blue (#001F3F)",
            "accent_color": "cyan (#00FFFF)",
            "main_element": "Ethereum symbol with neon glow",
            "background": "purple-blue gradient with abstract geometric shapes",
            "style": "digital art, vibrant gradients, modern"
        },
        "altcoins": {
            "primary_color": "vibrant yellow (#FFFF00)",
            "secondary_color": "neon green (#00FF00)",
            "accent_color": "electric blue (#0080FF)",
            "main_element": "Multiple cryptocurrency symbols arranged dynamically",
            "background": "gradient background with floating geometric elements",
            "style": "digital art, colorful, energetic"
        },
        "defi": {
            "primary_color": "neon green (#00FF00)",
            "secondary_color": "dark teal (#003333)",
            "accent_color": "bright yellow (#FFFF00)",
            "main_element": "Connected nodes and network visualization",
            "background": "dark background with glowing connection lines",
            "style": "digital art, network visualization, tech-forward"
        },
        "regulacao": {
            "primary_color": "royal blue (#0033AA)",
            "secondary_color": "gold (#FFD700)",
            "accent_color": "white (#FFFFFF)",
            "main_element": "Government building or official emblem with modern overlay",
            "background": "professional gradient with subtle geometric accents",
            "style": "digital art, institutional, modern overlay"
        },
        "airdrop": {
            "primary_color": "bright yellow (#FFFF00)",
            "secondary_color": "lime green (#00FF00)",
            "accent_color": "orange (#FF8800)",
            "main_element": "Token symbols with dynamic motion lines",
            "background": "vibrant gradient with energy effects",
            "style": "digital art, dynamic, celebratory"
        }
    }
    
    # Entidades conhecidas (mantido do v2.0)
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
    
    # Negative prompt atualizado para o novo estilo
    BASE_NEGATIVE_PROMPT = """text, letters, words, typography, watermark, signature, brand names,
blurry, low resolution, poor quality, amateur work,
realistic photography, photorealistic, photo, photograph,
3d render, cartoon, anime, manga, illustration, painting,
ugly, deformed, distorted, disfigured,
messy composition, cluttered, chaotic, unbalanced,
cheap stock photo aesthetic, corporate stock imagery"""
    
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
        """Converte nome de categoria para slug"""
        if not category_name:
            return "bitcoin"
        
        slug = category_name.lower()
        slug = slug.replace("ç", "c").replace("ã", "a").replace("õ", "o")
        
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
        
        return "bitcoin"
    
    def extract_entities(self, title: str, content: str) -> Dict[str, List[str]]:
        """Extrai entidades nomeadas do título e conteúdo"""
        text = f"{title.lower()} {content[:500].lower()}"
        
        entities = {
            "companies": [],
            "people": [],
            "protocols": [],
            "institutions": []
        }
        
        for category, entity_dict in self.KNOWN_ENTITIES.items():
            for entity_name, keywords in entity_dict.items():
                if any(keyword in text for keyword in keywords):
                    entities[category].append(entity_name)
        
        logger.debug(f"Entidades extraídas: {entities}")
        return entities
    
    def _extract_main_theme(self, title: str, content: str) -> str:
        """Extrai o tema principal da notícia"""
        text = f"{title} {content[:300]}".lower()
        
        theme_keywords = {
            "price surge": ["sobe", "alta", "dispara", "valoriza", "recorde", "máxima", "surge", "rally"],
            "price decline": ["cai", "queda", "desvaloriza", "crash", "bear", "correção"],
            "regulation": ["governo", "regulação", "lei", "senado", "congresso", "sec", "cvm"],
            "adoption": ["instituição", "empresa", "adoção", "corporação", "banco"],
            "technology": ["atualização", "upgrade", "tecnologia", "protocolo", "rede"],
            "security": ["hack", "ataque", "vulnerabilidade", "segurança"],
            "partnership": ["parceria", "acordo", "colaboração"],
            "launch": ["lança", "lançamento", "novo"],
            "etf": ["etf", "fundo", "aprovação"],
        }
        
        for theme, keywords in theme_keywords.items():
            if any(keyword in text for keyword in keywords):
                return theme
        
        return "market update"
    
    def build_dalle_prompt_v3(
        self,
        entities: Dict[str, List[str]],
        category: str,
        theme: str,
        title: str
    ) -> str:
        """
        Constrói o prompt para DALL-E 3 no estilo CoinDesk/CoinPaper (v3.0)
        
        Returns:
            Prompt completo para geração de arte digital abstrata
        """
        style_config = self.CATEGORY_VISUAL_STYLES.get(
            category, 
            self.CATEGORY_VISUAL_STYLES["bitcoin"]
        )
        
        # Construir descrição de entidades
        entity_mentions = []
        if entities["protocols"]:
            entity_mentions.append(f"{entities['protocols'][0]} cryptocurrency")
        if entities["companies"]:
            entity_mentions.append(f"{entities['companies'][0]} company")
        if entities["institutions"]:
            entity_mentions.append(f"{entities['institutions'][0]} institution")
        
        subject = " and ".join(entity_mentions) if entity_mentions else "cryptocurrency market"
        
        # Construir elementos visuais específicos baseados no tema
        theme_elements = {
            "price surge": "upward trending lines, glowing ascending arrows, explosive energy effects",
            "price decline": "downward trending lines, warning indicators, cooling color shifts",
            "regulation": "official emblems, institutional architecture overlay, formal geometric patterns",
            "adoption": "corporate logos subtly integrated, modern office environment overlay",
            "technology": "network nodes, connection lines, data flow visualization",
            "security": "shield symbols, lock icons, protective barriers",
            "partnership": "connecting lines between entities, handshake symbolism",
            "launch": "burst effects, celebration elements, spotlight effects",
            "etf": "financial charts, institutional approval symbols",
        }
        
        theme_visual = theme_elements.get(theme, "dynamic market visualization")
        
        prompt = f"""Digital art illustration for cryptocurrency news article about {subject}.

**Visual Style: CoinDesk/CoinPaper Editorial**
- Art Style: Modern digital art, abstract and geometric, high-tech aesthetic
- NOT photorealistic - this should be digital illustration/graphic design
- Similar to: CoinDesk featured images, CoinPaper editorial graphics

**Color Palette:**
- Primary: {style_config['primary_color']}
- Secondary: {style_config['secondary_color']}
- Accent: {style_config['accent_color']}
- High contrast, vibrant and bold colors

**Main Elements:**
- Central Focus: {style_config['main_element']}
- Background: {style_config['background']}
- Additional Elements: {theme_visual}

**Geometric Elements (CRITICAL):**
- Floating squares and rectangles in primary and accent colors
- Thin geometric connection lines creating network patterns
- Abstract shapes layered at different depths
- Glowing effects and light rays emanating from central element

**Composition:**
- Centered main subject with intense glow/highlight
- Geometric shapes scattered asymmetrically in corners and edges
- Layered depth with foreground, midground, and background elements
- Dynamic diagonal lines suggesting movement and energy
- Clean negative space to avoid clutter

**Lighting & Effects:**
- Intense glow around main cryptocurrency symbol/element
- Light rays or beams creating dramatic effect
- Gradient backgrounds (not solid colors)
- Neon-like highlights on geometric shapes
- High contrast between dark and bright areas

**Technical Specifications:**
- Resolution: High quality, sharp edges
- Style: {style_config['style']}
- Mood: Futuristic, dynamic, professional yet bold
- Format: Widescreen 16:9 ratio ideal for article headers

**AVOID:**
- Realistic photography or photorealistic rendering
- Human faces or realistic people
- Actual company logos or text
- Cluttered or messy compositions
- Dull or muted colors"""
        
        logger.info(f"Prompt v3.0 construído para categoria '{category}' e tema '{theme}'")
        return prompt
    
    async def generate_and_upload_image(
        self,
        title: str,
        content: str,
        category_name: Optional[str] = None
    ) -> str:
        """
        Gera imagem no estilo digital art e faz upload para Cloudinary (v3.0)
        
        Args:
            title: Título do artigo
            content: Conteúdo do artigo
            category_name: Nome da categoria do artigo
            
        Returns:
            URL da imagem no Cloudinary
        """
        try:
            logger.info(f"Gerando imagem digital art v3.0 para: {title[:50]}...")
            
            # Determinar categoria
            category_slug = self._get_category_slug(category_name)
            
            # Extrair entidades
            entities = self.extract_entities(title, content)
            
            # Extrair tema principal
            theme = self._extract_main_theme(title, content)
            
            # Construir prompt v3.0 (estilo CoinDesk/CoinPaper)
            final_prompt = self.build_dalle_prompt_v3(entities, category_slug, theme, title)
            
            logger.debug(f"Prompt final v3.0:\n{final_prompt}")
            
            # Gerar imagem com DALL-E 3
            response = self.client.images.generate(
                model="dall-e-3",
                prompt=final_prompt,
                size="1792x1024",  # Widescreen para header de artigo
                quality="hd",
                n=1,
                style="vivid"  # Vivid para cores mais vibrantes
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
            logger.error(f"Erro ao gerar/upload imagem v3.0: {e}")
            return ""

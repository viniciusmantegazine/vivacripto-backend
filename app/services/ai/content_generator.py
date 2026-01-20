"""
AI Content Generator Service v4.0
Gera conteúdo de notícias usando Google Gemini (primário) com OpenAI como fallback,
estrutura otimizada, guardrails de segurança e prevenção de alucinações
"""
import re
from typing import Dict, Optional

from loguru import logger
from openai import AsyncOpenAI
from slugify import slugify

from app.core.config import settings

# Google Gemini imports
try:
    from google import genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    logger.warning("Google GenAI SDK não instalado. Usando apenas OpenAI.")


# Configurações de tom por categoria
CATEGORY_CONFIG = {
    "bitcoin": {
        "tom": "Factual e analítico",
        "foco": "impacto no mercado e adoção institucional",
        "keywords": ["Bitcoin", "BTC", "criptomoeda"]
    },
    "ethereum": {
        "tom": "Técnico e educativo",
        "foco": "desenvolvimentos tecnológicos e ecossistema",
        "keywords": ["Ethereum", "ETH", "smart contracts"]
    },
    "altcoins": {
        "tom": "Informativo e cauteloso",
        "foco": "novidades e contexto de mercado",
        "keywords": ["altcoin", "criptomoeda", "token"]
    },
    "defi": {
        "tom": "Educativo e técnico",
        "foco": "explicação de protocolos e riscos",
        "keywords": ["DeFi", "finanças descentralizadas", "protocolo"]
    },
    "regulacao": {
        "tom": "Formal e analítico",
        "foco": "impacto regulatório e contexto legal",
        "keywords": ["regulação", "legislação", "compliance"]
    },
    "airdrop": {
        "tom": "Instrucional e direto",
        "foco": "informações práticas e requisitos",
        "keywords": ["airdrop", "distribuição", "tokens grátis"]
    },
    "default": {
        "tom": "Jornalístico equilibrado",
        "foco": "relevância para o mercado cripto brasileiro",
        "keywords": ["criptomoeda", "mercado cripto", "blockchain"]
    }
}


class ContentGenerator:
    """Gerador de conteúdo com IA v4.0 - Gemini + OpenAI fallback com guardrails anti-alucinação"""

    # Modelos
    GEMINI_MODEL = "gemini-2.5-flash"
    OPENAI_MODEL = "gpt-4o-mini"

    # System Prompt v3.0 - Estruturado com tags XML para melhor parsing
    SYSTEM_PROMPT = """<persona>
Você é o Editor-Chefe do portal VivaCripto, um veículo jornalístico especializado em criptoeconomia para o público brasileiro. Sua formação combina jornalismo financeiro (Bloomberg), tecnologia acessível (The Verge) e expertise cripto (CoinDesk).
</persona>

<audiencia>
Seu leitor é brasileiro, interessado em criptomoedas, e pode ser:
- Iniciante curioso buscando entender o mercado
- Investidor ativo querendo se manter informado
- Profissional de tecnologia acompanhando tendências

Escreva para TODOS esses perfis simultaneamente: claro para iniciantes, relevante para veteranos.
</audiencia>

<tom_de_voz>
- DIRETO: Vá ao ponto. Cada frase deve ter propósito.
- INFORMATIVO: Fatos > Opiniões. Dados > Especulações.
- EDUCATIVO: Explique termos técnicos naturalmente, sem parecer didático demais.
- NEUTRO: Sem sensacionalismo. Sem FOMO. Sem FUD.
</tom_de_voz>

<anti_patterns>
NUNCA use estas construções robóticas ou clichês:
- "Vale ressaltar que..."
- "Em conclusão..."
- "É importante mencionar que..."
- "Conforme mencionado anteriormente..."
- "Neste contexto..."
- "Diante do exposto..."
- "Sendo assim..."
- "Por fim..."
- "Em suma..."
- Iniciar múltiplas frases com "Além disso"
- Usar "the" ou anglicismos desnecessários
- Frases que começam com "Com a/o" repetidamente
</anti_patterns>

<guardrails_de_seguranca>
🚫 PROIBIÇÕES ABSOLUTAS - VIOLAÇÃO RESULTA EM REJEIÇÃO:

1. **DADOS INVENTADOS:**
   - NUNCA invente preços, porcentagens, datas, valores ou estatísticas que NÃO estejam EXPLICITAMENTE na fonte fornecida.
   - Se a fonte disser "Bitcoin subiu", NÃO escreva "Bitcoin subiu 5,3%" ou "atingiu US$ 70.000".
   - Quando não houver dados específicos, use termos como "registrou alta", "apresentou valorização", "sofreu queda".

2. **CONSELHO FINANCEIRO (NFA - Not Financial Advice):**
   NUNCA use linguagem que possa ser interpretada como recomendação de investimento:
   ❌ "Investidores devem considerar..."
   ❌ "O momento é propício para..."
   ❌ "Especialistas recomendam comprar/vender..."
   ❌ "É uma boa oportunidade para..."
   ❌ "Pode ser interessante aproveitar..."
   ✅ "A decisão de investimento cabe a cada indivíduo após própria análise."
   ✅ "Investidores devem fazer sua própria pesquisa (DYOR)."

3. **PREVISÕES ASSERTIVAS:**
   NUNCA faça previsões de preço ou afirmações sobre o futuro como fatos:
   ❌ "O Bitcoin vai atingir $100k"
   ❌ "O mercado certamente vai subir"
   ✅ "Alguns analistas projetam cenários otimistas, embora o mercado seja imprevisível."
   ✅ "O movimento pode indicar tendência, mas mercados cripto são voláteis."

4. **ATRIBUIÇÃO OBRIGATÓRIA:**
   Quando mencionar dados específicos, SEMPRE atribua à fonte:
   ✅ "Segundo a fonte original..."
   ✅ "De acordo com dados divulgados..."
   ✅ "Conforme reportado..."

5. **METADADOS NO OUTPUT:**
   NUNCA inicie o texto com prefixos como "Título:", "Resumo:", "Corpo:", "Artigo:", etc.
</guardrails_de_seguranca>

<formato_de_saida>
- Markdown puro (renderização direta no frontend)
- H2 (##) para subtítulo interno único da matéria
- **Negrito** para conceitos-chave e dados importantes
- Listas com hífen (-) quando houver 3+ itens relacionados
- Quebras de linha duplas (\\n\\n) entre TODOS os parágrafos
- Parágrafos com 2-4 frases cada (evite blocos muito longos)
- Alterne frases curtas e longas para ritmo natural
</formato_de_saida>"""

    def __init__(self):
        # OpenAI client (fallback)
        self.openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

        # Gemini client (primário)
        self.gemini_client = None
        self.use_gemini = False

        if GEMINI_AVAILABLE and settings.GEMINI_API_KEY:
            try:
                self.gemini_client = genai.Client(api_key=settings.GEMINI_API_KEY)
                self.use_gemini = True
                logger.info("ContentGenerator v4.0: Gemini configurado como primário")
            except Exception as e:
                logger.warning(f"Falha ao inicializar Gemini: {e}. Usando OpenAI como primário.")
        else:
            logger.info("ContentGenerator v4.0: Usando OpenAI (Gemini não disponível)")
    
    async def generate_article(self, source_news: Dict, category: str = "default") -> Optional[Dict]:
        """
        Gera um artigo completo a partir de uma notícia fonte (v3.0)

        Args:
            source_news: Notícia coletada das fontes
            category: Categoria do artigo para ajuste de tom (bitcoin, ethereum, defi, etc.)

        Returns:
            Artigo gerado com título, conteúdo, excerpt e meta tags
        """
        try:
            title = source_news.get("title", "")
            description = source_news.get("description", "")
            source = source_news.get("source", "")

            logger.info(f"Gerando artigo v3.0 para: {title[:50]}... (categoria: {category})")

            # Gerar conteúdo principal com categoria para ajuste de tom
            content = await self._generate_content(title, description, source, category)

            if not content:
                logger.warning("Falha ao gerar conteúdo")
                return None

            # Obter keyword da categoria para SEO
            cat_config = self._get_category_config(category)
            keyword = cat_config["keywords"][0] if cat_config["keywords"] else "criptomoeda"

            # Gerar título otimizado para SEO
            seo_title = await self._generate_seo_title(content, keyword)

            # Gerar excerpt
            excerpt = await self._generate_excerpt(content)

            # Gerar meta description
            meta_description = await self._generate_meta_description(content, seo_title, keyword)

            # Gerar slug
            slug = slugify(seo_title or title)

            article = {
                "title": seo_title or title,
                "slug": slug,
                "content_markdown": content,
                "excerpt": excerpt,
                "meta_title": seo_title,
                "meta_description": meta_description,
                "source_url": source_news.get("url"),
                "source_name": source,
                "category": category,
            }

            logger.info(f"Artigo v3.0 gerado com sucesso: {article['title']}")
            return article

        except Exception as e:
            logger.error(f"Erro ao gerar artigo: {e}")
            return None
    
    def _get_category_config(self, category: str) -> Dict:
        """Retorna configuração específica para a categoria"""
        category_lower = category.lower() if category else "default"
        return CATEGORY_CONFIG.get(category_lower, CATEGORY_CONFIG["default"])

    async def _generate_content(
        self,
        title: str,
        description: str,
        source: str,
        category: str = "default"
    ) -> Optional[str]:
        """Gera o conteúdo principal do artigo com estrutura otimizada v3.0"""

        # Obter configuração da categoria
        cat_config = self._get_category_config(category)
        keyword_principal = cat_config["keywords"][0] if cat_config["keywords"] else "criptomoeda"

        user_prompt = f"""<dados_da_fonte>
Fonte: {source}
Título Original: {title}
Conteúdo da Fonte: {description}
Categoria: {category}
</dados_da_fonte>

<configuracao_editorial>
Tom recomendado: {cat_config["tom"]}
Foco da cobertura: {cat_config["foco"]}
Palavra-chave principal: {keyword_principal}
</configuracao_editorial>

<tarefa>
Transforme os dados acima em um artigo jornalístico completo para o portal VivaCripto, seguindo a estrutura abaixo.
</tarefa>

<estrutura_do_artigo>

## [Manchete Interna H2]
Crie um subtítulo impactante e informativo que resuma o ângulo da matéria.
NÃO use clickbait. Foque no valor informativo real.

**Parágrafo 1 - Lead Jornalístico:**
Responda de forma direta: Quem? O quê? Quando? Onde? Por quê?
Use a técnica da pirâmide invertida - o essencial vem primeiro.
O leitor deve entender a notícia completa apenas lendo este parágrafo.

**Parágrafos 2-3 - Contexto e Profundidade:**
Desenvolva a notícia com detalhes PRESENTES NA FONTE.
⚠️ IMPORTANTE: Use APENAS dados que estão explicitamente na fonte fornecida.

Se a fonte mencionar termos técnicos, explique-os naturalmente:
- ETF: Fundo negociado em bolsa que replica o desempenho de um ativo
- Halving: Evento programado que reduz pela metade a recompensa de mineração
- DeFi: Ecossistema de finanças descentralizadas sem intermediários tradicionais
- Layer 2: Soluções de segunda camada para escalabilidade de blockchains
- Staking: Processo de bloquear criptomoedas para validar transações e receber recompensas

Adicione contexto histórico ou de mercado quando RELEVANTE e VERIFICÁVEL.

**Parágrafo Final - Impacto e Relevância:**
Explique por que isso importa para o leitor brasileiro.
Qual o impacto potencial para o mercado, tecnologia ou regulação?

⚠️ REGRA CRÍTICA: NÃO faça recomendações de investimento.
⚠️ NÃO preveja preços ou movimentos de mercado como certezas.
✅ Limite-se a analisar possíveis desdobramentos de forma neutra.

</estrutura_do_artigo>

<requisitos_tecnicos>
- Tamanho: 250-480 palavras (MÁXIMO ABSOLUTO: 500)
- Use a palavra-chave "{keyword_principal}" naturalmente 2-3 vezes no texto
- Idioma: Português brasileiro fluente e natural
- Formatação: Quebras de linha duplas (\\n\\n) entre TODOS os parágrafos
- Estrutura: 3-5 parágrafos conforme necessidade do conteúdo
</requisitos_tecnicos>

<validacao_obrigatoria>
Antes de finalizar, VERIFIQUE mentalmente cada item:

☐ DADOS: Todos os números, preços, datas e porcentagens vieram da fonte original?
   → Se NÃO estão na fonte, NÃO invente. Use termos vagos ("registrou alta", "apresentou queda").

☐ NFA: Existe alguma frase que soa como conselho de investimento?
   → Se SIM, reformule para tom neutro e informativo.

☐ FLUÊNCIA: O texto flui naturalmente sem frases robóticas?
   → Evite: "Vale ressaltar", "Em conclusão", "É importante mencionar".

☐ CLAREZA: Um iniciante conseguiria entender? Um veterano acharia relevante?
   → Balance profundidade técnica com acessibilidade.

☐ COESÃO: O artigo tem início, meio e fim bem conectados?
   → Use transições naturais entre parágrafos.

☐ ATRIBUIÇÃO: Dados específicos estão atribuídos à fonte?
   → Use: "Segundo informações divulgadas...", "De acordo com a fonte..."
</validacao_obrigatoria>

<output>
Escreva APENAS o artigo final em Markdown, começando diretamente pelo H2.
Nenhum texto adicional, prefixo ou metadado.
</output>"""

        # Combinar system prompt com user prompt para Gemini (não tem system message separado)
        full_prompt = f"{self.SYSTEM_PROMPT}\n\n{user_prompt}"

        content = None

        # Tentar Gemini primeiro
        if self.use_gemini and self.gemini_client:
            try:
                logger.info(f"[Gemini] Gerando conteúdo com {self.GEMINI_MODEL}...")
                response = await self.gemini_client.aio.models.generate_content(
                    model=self.GEMINI_MODEL,
                    contents=full_prompt,
                )
                content = response.text.strip()
                logger.info("[Gemini] Conteúdo gerado com sucesso")
            except Exception as e:
                logger.warning(f"[Gemini] Falha na geração: {e}. Tentando OpenAI como fallback...")

        # Fallback para OpenAI se Gemini falhou ou não está disponível
        if content is None:
            try:
                logger.info(f"[OpenAI] Gerando conteúdo com {self.OPENAI_MODEL}...")
                response = await self.openai_client.chat.completions.create(
                    model=self.OPENAI_MODEL,
                    messages=[
                        {"role": "system", "content": self.SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.4,
                    max_tokens=900,
                )
                content = response.choices[0].message.content.strip()
                logger.info("[OpenAI] Conteúdo gerado com sucesso (fallback)")
            except Exception as e:
                logger.error(f"[OpenAI] Erro ao gerar conteúdo: {e}")
                return None

        # Debug: Mostrar conteúdo bruto da IA
        logger.debug(f"Conteúdo bruto da IA (primeiros 300 chars): {content[:300]}")

        # Sanitização adicional (failsafe)
        content = self._sanitize_content(content)

        # Debug: Mostrar conteúdo após sanitização
        logger.debug(f"Conteúdo após sanitização (primeiros 300 chars): {content[:300]}")

        # Verificar quebras de linha
        double_breaks = content.count('\n\n')
        word_count = len(content.split())
        logger.info(f"Artigo gerado - Quebras duplas: {double_breaks}, Palavras: {word_count}")

        return content
    
    def _sanitize_content(self, content: str) -> str:
        """
        Sanitiza o conteúdo gerado pela IA (v3.0)

        Realiza:
        1. Remoção de prefixos de metadados vazados
        2. Detecção de frases de conselho financeiro (warning)
        3. Detecção de frases robóticas/clichês (warning)
        4. Normalização de formatação

        Args:
            content: Conteúdo bruto da IA

        Returns:
            Conteúdo limpo e validado
        """
        # Lista de prefixos proibidos (metadados)
        forbidden_prefixes = [
            "Título:", "Titulo:", "Resumo:", "Corpo:", "Artigo:",
            "Conteúdo:", "Conteudo:", "Texto:", "Notícia:", "Noticia:",
            "Meta:", "Output:", "Resposta:",
            "**Título:**", "**Titulo:**", "**Resumo:**",
            "**Corpo:**", "**Artigo:**", "**Output:**",
        ]

        # Frases que indicam possível conselho financeiro (apenas warning)
        nfa_red_flags = [
            "devem considerar comprar",
            "devem considerar vender",
            "recomendamos",
            "aconselhamos",
            "é hora de comprar",
            "é hora de vender",
            "aproveite para",
            "não perca a oportunidade",
            "momento ideal para investir",
            "você deveria investir",
        ]

        # Frases robóticas a detectar (apenas warning para log)
        robotic_phrases = [
            "vale ressaltar que",
            "é importante mencionar",
            "em conclusão",
            "diante do exposto",
            "neste contexto",
            "conforme mencionado anteriormente",
            "sendo assim",
            "em suma",
            "por fim,",
        ]

        # Remover prefixos linha por linha, PRESERVANDO quebras duplas
        lines = content.split('\n')
        cleaned_lines = []

        for line in lines:
            line_stripped = line.strip()

            # Se linha está vazia, preservar para manter quebras de parágrafo
            if not line_stripped:
                cleaned_lines.append('')
                continue

            # Verificar se linha começa com prefixo proibido
            for prefix in forbidden_prefixes:
                if line_stripped.startswith(prefix):
                    line = line_stripped[len(prefix):].strip()
                    logger.warning(f"[Sanitização] Removido prefixo proibido: {prefix}")
                    break

            cleaned_lines.append(line)

        # Juntar linhas preservando estrutura
        result = '\n'.join(cleaned_lines)

        # Remover múltiplas quebras consecutivas (mais de 2)
        result = re.sub(r'\n{3,}', '\n\n', result)

        # Verificar red flags de NFA (apenas log warning, não bloqueia)
        content_lower = result.lower()
        for phrase in nfa_red_flags:
            if phrase in content_lower:
                logger.warning(f"[NFA Alert] Detectada possível linguagem de conselho financeiro: '{phrase}'")

        # Verificar frases robóticas (apenas log warning)
        for phrase in robotic_phrases:
            if phrase in content_lower:
                logger.warning(f"[Qualidade] Detectada frase robótica/clichê: '{phrase}'")

        return result.strip()
    
    async def _generate_seo_title(self, content: str, keyword: str = "criptomoeda") -> Optional[str]:
        """Gera título otimizado para SEO (v3.0 com few-shot examples)"""

        prompt = f"""<contexto>
Artigo: {content[:500]}
Palavra-chave principal: {keyword}
</contexto>

<tarefa>
Crie um título SEO otimizado para este artigo sobre criptomoedas.
</tarefa>

<requisitos>
- 50-70 caracteres (ideal: 60)
- Inclua "{keyword}" preferencialmente no início ou meio do título
- Seja atrativo mas NUNCA clickbait sensacionalista
- Use verbos de ação quando apropriado (Revela, Anuncia, Lança, Atinge, Supera)
- Português brasileiro fluente
</requisitos>

<exemplos>
✅ BONS títulos (use como referência de estilo):
- "Bitcoin Atinge Máxima Histórica Após Aprovação de ETF nos EUA"
- "Ethereum Anuncia Data do Upgrade Dencun: O Que Muda Para Usuários"
- "SEC Processa Binance por Irregularidades: Entenda o Caso"
- "Solana Supera Ethereum em Volume de DEX Pela Primeira Vez"
- "Brasil Avança em Regulação Cripto: Novo Marco Legal em Discussão"

❌ RUINS (NUNCA faça assim):
- "URGENTE: Bitcoin VAI EXPLODIR! Não Perca!!!" (clickbait extremo)
- "Notícia importante sobre Bitcoin" (genérico demais)
- "O Mercado de Criptomoedas e as Implicações Regulatórias Internacionais..." (muito longo)
- "Você não vai acreditar no que aconteceu com o Ethereum" (clickbait)
</exemplos>

<output>
Retorne APENAS o título, sem aspas, prefixos ou explicações.
</output>"""

        system_instruction = "Você é um especialista em SEO para portais de notícias cripto. Crie títulos precisos, informativos e otimizados para buscadores."
        full_prompt = f"{system_instruction}\n\n{prompt}"

        title = None

        # Tentar Gemini primeiro
        if self.use_gemini and self.gemini_client:
            try:
                response = await self.gemini_client.aio.models.generate_content(
                    model=self.GEMINI_MODEL,
                    contents=full_prompt,
                )
                title = response.text.strip()
            except Exception as e:
                logger.warning(f"[Gemini] Falha ao gerar título SEO: {e}")

        # Fallback para OpenAI
        if title is None:
            try:
                response = await self.openai_client.chat.completions.create(
                    model=self.OPENAI_MODEL,
                    messages=[
                        {"role": "system", "content": system_instruction},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.5,
                    max_tokens=60,
                )
                title = response.choices[0].message.content.strip()
            except Exception as e:
                logger.error(f"[OpenAI] Erro ao gerar título SEO: {e}")
                return None

        # Remover aspas e prefixos comuns
        title = title.strip('"\'')
        title = re.sub(r'^(Título|Titulo|Title):\s*', '', title, flags=re.IGNORECASE).strip()
        return title
    
    async def _generate_excerpt(self, content: str) -> Optional[str]:
        """Gera excerpt do artigo"""
        # Remover markdown e pegar primeiras 2 frases
        clean_content = content.replace('**', '').replace('##', '').replace('*', '')
        sentences = clean_content.split('. ')[:2]
        excerpt = '. '.join(sentences)
        
        # Limitar a 150 caracteres
        if len(excerpt) > 150:
            excerpt = excerpt[:147] + "..."
        
        return excerpt
    
    async def _generate_meta_description(
        self,
        content: str,
        title: str = "",
        keyword: str = "criptomoeda"
    ) -> Optional[str]:
        """Gera meta description para SEO (v3.0 com few-shot examples)"""

        prompt = f"""<contexto>
Artigo: {content[:500]}
Título SEO: {title}
Palavra-chave: {keyword}
</contexto>

<tarefa>
Crie uma meta description SEO para este artigo sobre criptomoedas.
</tarefa>

<requisitos>
- 140-160 caracteres (ideal: 155)
- Inclua "{keyword}" de forma natural
- Resuma o VALOR do artigo para o leitor
- Termine com curiosidade ou CTA implícito (sem "clique aqui")
- Português brasileiro fluente
- Complemente o título, não repita
</requisitos>

<exemplos>
✅ BOAS meta descriptions:
- "Entenda como a aprovação do ETF de Bitcoin nos EUA pode impactar o mercado cripto brasileiro e o que esperar nos próximos meses."
- "SEC processa Binance por irregularidades. Veja os detalhes do caso e as possíveis consequências para investidores no Brasil."
- "Upgrade Dencun promete reduzir taxas do Ethereum em até 90%. Saiba quando entra em vigor e como afeta suas transações."
- "Solana registra recorde de transações e supera Ethereum em volume. Analistas avaliam se tendência deve continuar."

❌ RUINS:
- "Leia nossa notícia sobre Bitcoin. Clique aqui para saber mais." (genérico, CTA explícito)
- "Bitcoin Bitcoin Bitcoin criptomoeda crypto moeda digital blockchain" (keyword stuffing)
- "Notícia muito importante sobre o mercado" (vago, sem valor)
</exemplos>

<output>
Retorne APENAS a meta description, sem aspas ou prefixos.
</output>"""

        system_instruction = "Você é um especialista em SEO para portais de notícias cripto. Crie meta descriptions que aumentam CTR nos resultados de busca."
        full_prompt = f"{system_instruction}\n\n{prompt}"

        meta_desc = None

        # Tentar Gemini primeiro
        if self.use_gemini and self.gemini_client:
            try:
                response = await self.gemini_client.aio.models.generate_content(
                    model=self.GEMINI_MODEL,
                    contents=full_prompt,
                )
                meta_desc = response.text.strip()
            except Exception as e:
                logger.warning(f"[Gemini] Falha ao gerar meta description: {e}")

        # Fallback para OpenAI
        if meta_desc is None:
            try:
                response = await self.openai_client.chat.completions.create(
                    model=self.OPENAI_MODEL,
                    messages=[
                        {"role": "system", "content": system_instruction},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.3,
                    max_tokens=80,
                )
                meta_desc = response.choices[0].message.content.strip()
            except Exception as e:
                logger.error(f"[OpenAI] Erro ao gerar meta description: {e}")
                return None

        # Remover aspas e prefixos comuns
        meta_desc = meta_desc.strip('"\'')
        meta_desc = re.sub(r'^(Meta description|Descrição|Description):\s*', '', meta_desc, flags=re.IGNORECASE).strip()

        # Garantir que não exceda 160 caracteres
        if len(meta_desc) > 160:
            meta_desc = meta_desc[:157] + "..."

        return meta_desc

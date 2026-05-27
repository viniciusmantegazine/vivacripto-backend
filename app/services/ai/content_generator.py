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
Você é o Editor-Chefe do portal VivaCripto, um veículo jornalístico especializado em criptoeconomia para o público brasileiro. Sua formação combina jornalismo financeiro (Bloomberg), tecnologia acessível (The Verge) e expertise no mercado cripto.
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
- "Vale destacar que..."
- "Em conclusão..."
- "É importante mencionar que..."
- "Conforme mencionado anteriormente..."
- "Neste contexto..."
- "Diante do exposto..."
- "Sendo assim..."
- "Por fim..."
- "Em suma..."

🚫 NUNCA use estas frases vagas de atribuição — são o "fingerprint" de conteúdo gerado por IA que o Google detecta e penaliza:
- "Segundo informações divulgadas..."
- "Conforme informações divulgadas..."
- "De acordo com dados do mercado..."
- "Conforme reportado..."
- "Fontes do setor indicam..."
- "Este movimento reflete..."
- "Conforme análises recentes..."
- "De acordo com análises recentes..."

NUNCA:
- Inicie múltiplas frases com "Além disso"
- Use anglicismos desnecessários
- Comece frases com "Com a/o" repetidamente
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

4. **ATRIBUIÇÃO À FONTE PRIMÁRIA (não a veículos):**
   Quando mencionar dados, declarações ou eventos, atribua sempre ao EMISSOR REAL da informação — quem produziu o dado/declaração — e NÃO a veículos jornalísticos intermediários.

   ✅ ATRIBUIÇÕES VÁLIDAS (emissor primário, verificável):
   - "Segundo o relatório oficial da [empresa/projeto]..."
   - "De acordo com comunicado da SEC..."
   - "Em entrevista, [nome do executivo, com cargo] afirmou que..."
   - "O whitepaper do projeto detalha que..."
   - "Dados on-chain da [Glassnode/CoinGecko/Chainalysis/Dune] mostram que..."
   - "A análise técnica do gráfico de [par] indica..."
   - "Conforme post oficial no X (Twitter) da [empresa]..."
   - "O CEO da [empresa], [nome], publicou que..."

   ❌ ATRIBUIÇÕES INVÁLIDAS (vagas — fingerprint de IA):
   - "Segundo informações divulgadas..."
   - "Conforme reportado..."
   - "De acordo com dados do mercado..."
   - "Fontes do setor indicam..."

   ⚠️ Se a notícia fonte não tornar clara a fonte primária, prefira REFORMULAR o fato sem atribuição direta em vez de usar atribuição vaga.

5. **METADADOS NO OUTPUT:**
   NUNCA inicie o texto com prefixos como "Título:", "Resumo:", "Corpo:", "Artigo:", etc.

6. **NÃO MENCIONE VEÍCULOS JORNALÍSTICOS CONCORRENTES:**
   NUNCA mencione nomes de sites de notícias cripto no texto gerado.

   Sites PROIBIDOS de citar: CoinDesk, CoinTelegraph, Cointelegraph, CryptoSlate, Bitcoin Magazine, Decrypt, The Block, CoinPaper, CoinRepo, BeInCrypto, NewsBTC, CryptoNews.

   ⚠️ IMPORTANTE: A regra é NÃO usar veículos como atribuição — mas isso NÃO significa usar frases vagas como "segundo informações divulgadas" (proibidas no item 4 e nos anti_patterns).

   ✅ Caminho correto: atribua à FONTE PRIMÁRIA (empresa, regulador, executivo, relatório oficial, dados on-chain) — ver item 4.

   ✅ Provedores de DADOS técnicos PODEM ser citados (não são veículos jornalísticos):
   - CoinGecko, CoinMarketCap, Glassnode, Chainalysis, Dune Analytics, Messari, DefiLlama, Nansen, TradingView.

   Se a notícia original só cita o veículo e não a fonte primária, REFORMULE o fato sem atribuição em vez de usar frase vaga.
</guardrails_de_seguranca>

<formato_de_saida>
- Markdown puro (renderização direta no frontend)
- H2 (##) para subtítulo interno único da matéria
- **Negrito** para conceitos-chave e dados importantes
- Listas com hífen (-) quando houver 3+ itens relacionados
- Quebras de linha duplas (\\n\\n) entre TODOS os parágrafos
- Parágrafos com 2-4 frases cada (evite blocos muito longos)
- Alterne frases curtas e longas para ritmo natural
</formato_de_saida>

<requisitos_criticos>
⚠️ REQUISITOS DE VALIDAÇÃO AUTOMÁTICA - O artigo será REJEITADO se não cumprir:

1. MÍNIMO 250 PALAVRAS: Artigos curtos demais são rejeitados. Desenvolva bem cada parágrafo.
2. KEYWORDS OBRIGATÓRIAS: O texto DEVE conter termos como "criptomoeda", "cripto", "Bitcoin", "Ethereum", "blockchain", "token" ou "DeFi".
3. ESTRUTURA H2: O artigo DEVE começar com ## (heading de nível 2).
</requisitos_criticos>"""

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
Título Original: {title}
Conteúdo da Fonte: {description}
Categoria: {category}
</dados_da_fonte>

<regra_fonte>
⚠️ REGRA CRÍTICA DE ATRIBUIÇÃO:

1. NÃO mencione nomes de VEÍCULOS jornalísticos concorrentes (CoinDesk, CoinTelegraph, Bitcoin Magazine, CryptoSlate, Decrypt, The Block, BeInCrypto, NewsBTC).

2. TAMBÉM NÃO use frases vagas como substituto — elas são fingerprint de IA que o Google penaliza:
   ❌ PROIBIDO: "segundo informações divulgadas", "conforme reportado", "de acordo com dados do mercado", "fontes do setor indicam".

3. CAMINHO CORRETO: atribua à FONTE PRIMÁRIA — quem produziu/emitiu a informação:
   ✅ Empresa/projeto: "Segundo o relatório da [nome da empresa]..."
   ✅ Regulador: "De acordo com comunicado da SEC/CVM/SFC..."
   ✅ Executivo: "[Nome], CEO da [empresa], afirmou que..."
   ✅ Documento técnico: "O whitepaper detalha que..."
   ✅ Provedor de dados (não é veículo): "Dados da Glassnode/CoinGecko/Chainalysis/Dune mostram..."

4. Se a fonte primária não estiver clara na notícia original, REFORMULE o fato em voz direta sem atribuir — não use atribuição vaga.
</regra_fonte>

<configuracao_editorial>
Tom recomendado: {cat_config["tom"]}
Foco da cobertura: {cat_config["foco"]}
Palavra-chave principal: {keyword_principal}
</configuracao_editorial>

<tarefa>
Transforme os dados acima em um artigo jornalístico completo para o portal VivaCripto, seguindo a estrutura abaixo.
</tarefa>

<estrutura_do_artigo>
O artigo deve ter ESTRUTURA HIERÁRQUICA com múltiplos subtítulos H2 — cada um cobrindo uma seção distinta, NÃO parafraseando o título principal. Estrutura obrigatória:

## [Manchete Interna H2 — ângulo principal da matéria]
Subtítulo informativo, sem clickbait, que abra um ângulo específico (não repetir o título).

**Lead jornalístico (1 parágrafo):**
Responda Quem? O quê? Quando? Onde? Por quê? em 3-5 frases.
Use pirâmide invertida — o essencial vem primeiro.
O leitor deve entender a notícia completa apenas lendo este parágrafo.

## [H2 — Contexto e detalhes]
**2-3 parágrafos** desenvolvendo a notícia com dados PRESENTES NA FONTE.

Se a fonte mencionar termos técnicos, explique-os naturalmente (sem parecer didático):
- ETF: Fundo negociado em bolsa que replica o desempenho de um ativo
- Halving: Evento programado que reduz pela metade a recompensa de mineração
- DeFi: Ecossistema de finanças descentralizadas sem intermediários tradicionais
- Layer 2: Soluções de segunda camada para escalabilidade de blockchains
- Staking: Processo de bloquear criptomoedas para validar transações e receber recompensas

Adicione contexto histórico ou de mercado quando RELEVANTE e VERIFICÁVEL na fonte.

⚠️ Use APENAS dados que estão explicitamente na fonte. NÃO invente números, datas, percentuais.

## [H2 — Impacto no Brasil] (OBRIGATÓRIO)
**1-2 parágrafos** com ângulo brasileiro específico. Esta seção é o diferencial editorial — sem ela, o artigo é apenas tradução de conteúdo gringo (Google penaliza).

Aborde pelo menos UM destes ângulos (o que fizer mais sentido pra notícia):
- Regulação: como CVM, BCB, Lei 14.478/2022 (marco cripto BR), Receita Federal afetam ou são afetados.
- Mercado local: impacto em exchanges nacionais (Mercado Bitcoin, Foxbit, NovaDAX, BitPreço), liquidez em real, paridade BTC/BRL.
- Investidor BR: impacto fiscal (IN 1.888 da Receita), tributação de ganho de capital cripto, declaração de IR.
- Comparação: como o fato se compara a iniciativas/regulação brasileiras similares.

Se nenhum ângulo BR for aplicável, mencione brevemente por que e como o leitor brasileiro pode acompanhar o desenrolar.

## [H2 — Próximos passos / O que observar]
**1 parágrafo** de fechamento analítico (NÃO conclusivo robótico).

Indique o que observar a seguir: próximas datas, votações, releases, eventos. Conecte ao contexto maior do mercado cripto.

⚠️ REGRAS CRÍTICAS:
- NÃO faça recomendações de investimento.
- NÃO preveja preços/movimentos como certezas.
- NÃO use frases robóticas de fechamento ("em conclusão", "por fim", "em suma").
- ✅ Limite-se a analisar possíveis desdobramentos de forma neutra.
</estrutura_do_artigo>

<requisitos_tecnicos>
⚠️ REQUISITOS OBRIGATÓRIOS - ARTIGO SERÁ REJEITADO SE NÃO CUMPRIR:

1. CONTAGEM DE PALAVRAS:
   - MÍNIMO ABSOLUTO: 700 palavras (artigos com menos serão REJEITADOS)
   - IDEAL: 900-1200 palavras
   - MÁXIMO: 1500 palavras
   → Profundidade real, não enchimento. Cada parágrafo deve agregar informação ou contexto novo.

2. PALAVRAS-CHAVE OBRIGATÓRIAS:
   O artigo DEVE conter pelo menos UMA destas palavras (validação automática):
   - "Bitcoin", "BTC", "Ethereum", "ETH", "crypto", "criptomoeda"
   - "blockchain", "DeFi", "NFT", "token", "moeda digital"
   → Use "{keyword_principal}" 3-5 vezes (densidade natural) E variações como "criptomoeda" ou "cripto".

3. FORMATAÇÃO:
   - Idioma: Português brasileiro fluente
   - Quebras de linha duplas (\\n\\n) entre TODOS os parágrafos
   - 4 seções H2 distintas (manchete, contexto, impacto Brasil, próximos passos)
   - Parágrafos com 3-5 frases cada (evite blocos extremos: nem 1 frase, nem 10)

4. ESTRUTURA H2:
   - O artigo DEVE começar com ## (heading H2)
   - DEVE conter PELO MENOS 3 H2s distintos (não parafrasear o título principal)
   - Cada H2 abre uma seção temática diferente
</requisitos_tecnicos>

<validacao_obrigatoria>
⚠️ CHECKLIST CRÍTICO - Verifique TODOS os itens antes de finalizar:

☐ CONTAGEM: O artigo tem entre 700 e 1500 palavras?
   → Se estiver curto, EXPANDA com contexto verificável, não com enchimento.
   → Se passou de 1500, CORTE redundâncias.

☐ KEYWORDS: O texto contém "criptomoeda", "cripto", "Bitcoin", "blockchain" ou similar?
   → Inclua 3-5 termos cripto naturalmente — não force keyword stuffing.

☐ DADOS: Todos os números, preços, datas e porcentagens vieram da fonte original?
   → Se NÃO estão na fonte, NÃO invente. Use termos qualitativos ("registrou alta", "apresentou queda").

☐ NFA: Existe alguma frase que soa como conselho de investimento?
   → Se SIM, reformule para tom neutro e informativo.

☐ FLUÊNCIA: O texto flui sem frases-tique de IA?
   → PROIBIDAS: "vale ressaltar", "em conclusão", "é importante mencionar", "segundo informações divulgadas", "conforme reportado", "fontes do setor indicam", "este movimento reflete".

☐ ESTRUTURA: O artigo tem 4 seções H2 distintas, cada uma com 1-3 parágrafos?
   → 4 H2s: Manchete principal, Contexto/Detalhes, Impacto no Brasil, Próximos passos.
   → H2s NÃO podem parafrasear o título principal — cada um cobre seção diferente.

☐ SEÇÃO BRASIL: O artigo tem uma seção específica com ângulo brasileiro (regulação CVM/BCB, exchanges nacionais, tributação)?
   → Esta seção é OBRIGATÓRIA. Sem ela = artigo rejeitado.

☐ ATRIBUIÇÃO: Dados específicos estão atribuídos à FONTE PRIMÁRIA (não a veículos nem a frases vagas)?
   → ✅ "Segundo relatório da [empresa]...", "De acordo com comunicado da SEC...", "Dados da Glassnode..."
   → ❌ "Segundo informações divulgadas...", "Conforme reportado...", "Fontes do setor..."
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
                    max_tokens=2500,
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

        # Nomes de sites/fontes de notícias que NUNCA devem aparecer no texto gerado
        source_site_names = [
            "CoinDesk", "Coindesk", "coindesk",
            "CoinTelegraph", "Cointelegraph", "cointelegraph",
            "CryptoSlate", "cryptoslate",
            "Bitcoin Magazine", "bitcoin magazine",
            "Decrypt", "decrypt",
            "The Block", "the block",
            "CoinPaper", "coinpaper",
            "CoinRepo", "coinrepo",
            "BeInCrypto", "beincrypto",
            "NewsBTC", "newsbtc",
            "CryptoNews", "cryptonews",
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

        # Remover menções a veículos jornalísticos concorrentes (v4.0)
        # ATENÇÃO: NÃO injetar frases-tique como "informações divulgadas"/"fontes do setor"
        # — esse é o fingerprint de IA que o Google penaliza. Se o LLM violou o prompt,
        # remover a frase introdutória inteira e logar ERROR para investigação.
        for site_name in source_site_names:
            if site_name in result:
                logger.error(
                    f"[Sanitização CRÍTICA] LLM violou regra e citou veículo '{site_name}'. "
                    f"Removendo frase atributiva. Revisar prompt se reincidir."
                )
                # Remover frase introdutória completa: "Segundo o CoinDesk, ..."
                result = re.sub(
                    rf'(?i)\b(segundo|de acordo com|conforme|para|por)\s+(o|a|o portal|o site)?\s*{re.escape(site_name)}\b\s*[,.]?\s*',
                    '',
                    result
                )
                # Remover construções "o CoinDesk informou/reportou/publicou X" -> "X"
                result = re.sub(
                    rf'(?i)\b(o|a|o portal|o site)?\s*{re.escape(site_name)}\s+(informou|reportou|publicou|divulgou|noticiou|revelou)\s+que\s+',
                    '',
                    result
                )
                # Remoção final: deletar qualquer ocorrência restante do nome
                if site_name in result:
                    result = result.replace(site_name, "")

        # Limpar artefatos de remoção (espaços duplos, vírgulas órfãs).
        # Restrito a [ \t] para NÃO colapsar \n\n — o validador exige quebras
        # duplas entre parágrafos (quality_validator._validate_content_structure).
        result = re.sub(r'[ \t]{2,}', ' ', result)
        result = re.sub(r'[ \t]+([,.;:])', r'\1', result)
        result = re.sub(r'([,.;:])[ \t]*\1+', r'\1', result)

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

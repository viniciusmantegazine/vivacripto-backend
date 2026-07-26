"""
AI Content Generator Service v4.0
Gera conteúdo de notícias usando Google Gemini (primário) com OpenAI como fallback,
estrutura otimizada, guardrails de segurança e prevenção de alucinações
"""
import json
import re
from typing import Dict, Optional

import json_repair
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

    # Veículos jornalísticos concorrentes que NUNCA devem aparecer no texto
    # gerado. SEM variantes de caixa: o casamento é por regex com
    # re.IGNORECASE. Reintroduzir "coindesk" ao lado de "CoinDesk" é o que
    # causou a corrupção de texto corrigida aqui.
    SOURCE_SITE_NAMES = (
        "CoinDesk",
        "CoinTelegraph",
        "CryptoSlate",
        "Bitcoin Magazine",
        "Decrypt",
        "The Block",
        "CoinPaper",
        "CoinRepo",
        "BeInCrypto",
        "NewsBTC",
        "CryptoNews",
    )

    # Exceção: "the block" (artigo + substantivo) é vocabulário central de
    # cripto — "the block height", "the block reward", "the block size".
    # Casar este nome case-SENSITIVE preserva essas frases e ainda pega
    # "The Block informou que...", porque LLM capitaliza nome próprio.
    # Custo aceito: menção ao veículo escrita toda em minúscula escapa.
    CASE_SENSITIVE_SITE_NAMES = frozenset({"The Block"})

    # Campos que o LLM precisa entregar para o artigo existir. excerpt e
    # meta_description ficam de fora de propósito: são recuperáveis, e
    # descartar um artigo de 2500 tokens por causa deles repetiria o defeito
    # que esta consolidação corrige.
    REQUIRED_ARTICLE_FIELDS = ("content_markdown", "title")

    # Faixa de excerpt que o QualityValidator aceita. Duplicada aqui de
    # propósito: precisamos decidir o fallback antes da validação, não depois
    # de o artigo ser reprovado.
    MIN_EXCERPT_LENGTH = 80
    MAX_EXCERPT_LENGTH = 200

    # Contrato de saída. As faixas têm dois níveis: a meta apertada é o ponto
    # ideal de SEO, o limite absoluto é a fronteira em que o QualityValidator
    # reprova. Declarar os dois evita que o modelo mire no limite e resvale.
    JSON_CONTRACT_BLOCK = """
<saida_json>
Responda APENAS com um objeto JSON válido. Sem cercas de código, sem texto antes ou depois.

{{
  "content_markdown": "o artigo completo em Markdown, começando por ##",
  "title": "título SEO",
  "excerpt": "resumo curto do artigo",
  "meta_description": "meta description SEO"
}}

REGRAS DE CADA CAMPO:

content_markdown — o artigo conforme <estrutura_do_artigo> e <requisitos_tecnicos> acima.
  ⚠️ Escape corretamente as quebras de linha (\\n) e as aspas (\\") dentro da string JSON.

title — alvo 50 a 70 caracteres (limite absoluto: 30 a 100).
  - Inclua "{keyword}" preferencialmente no início ou meio
  - Atrativo, mas NUNCA clickbait sensacionalista
  - Verbos de ação quando apropriado (Revela, Anuncia, Lança, Atinge, Supera)
  - Português brasileiro fluente
  BONS: "Bitcoin Atinge Máxima Histórica Após Aprovação de ETF nos EUA" /
     "Ethereum Anuncia Data do Upgrade Dencun: O Que Muda Para Usuários" /
     "SEC Processa Binance por Irregularidades: Entenda o Caso"
  RUINS: "URGENTE: Bitcoin VAI EXPLODIR! Não Perca!!!" (clickbait) /
     "Notícia importante sobre Bitcoin" (genérico) /
     "Você não vai acreditar no que aconteceu com o Ethereum" (clickbait)

excerpt — alvo 120 a 180 caracteres (limite absoluto: 80 a 200).
  - Resuma a notícia em 1 ou 2 frases COMPLETAS
  - Não repita o título literalmente
  - NUNCA termine no meio de uma frase

meta_description — alvo 140 a 160 caracteres (limite absoluto: 120 a 180).
  - Inclua "{keyword}" de forma natural
  - Resuma o VALOR do artigo para o leitor
  - Termine com curiosidade ou CTA implícito (sem "clique aqui")
  - Complemente o título, não repita
  BOAS: "Entenda como a aprovação do ETF de Bitcoin nos EUA pode impactar o
     mercado cripto brasileiro e o que esperar nos próximos meses."
  RUINS: "Leia nossa notícia sobre Bitcoin. Clique aqui para saber mais."
     (genérico, CTA explícito) / "Bitcoin Bitcoin criptomoeda crypto blockchain"
     (keyword stuffing)
</saida_json>"""

    # Seção de dados de mercado. Condicional: só entra quando o pipeline
    # conseguiu coletar. O "apenas se pertinente" evita que o modelo enfie
    # preço numa notícia de regulação só porque o número está ali.
    MARKET_DATA_BLOCK = """
<dados_de_mercado>
Dados VERIFICADOS de mercado, coletados em tempo real. São fonte válida para
citar números — use-os apenas se forem pertinentes ao fato noticiado, e deixe
claro que se referem ao momento da publicação.

{market_data}
</dados_de_mercado>
"""

    # Corpo do prompt do artigo. Copiado da f-string de _generate_content e
    # convertido em template com campos nomeados, para servir à chamada única.
    # A seção <output> antiga NÃO vem: ela pedia "APENAS o artigo em Markdown",
    # o que contradiz o contrato JSON acima.
    _ARTICLE_PROMPT_TEMPLATE = """<dados_da_fonte>
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
Tom recomendado: {tom}
Foco da cobertura: {foco}
Palavra-chave principal: {keyword}
</configuracao_editorial>

<tarefa>
Transforme os dados acima em um artigo jornalístico completo para o portal VerticeCripto, seguindo a estrutura abaixo.
</tarefa>

<estrutura_do_artigo>
O artigo deve ter ESTRUTURA HIERÁRQUICA com múltiplos subtítulos H2 — cada um cobrindo uma seção distinta, NÃO parafraseando o título principal. Estrutura obrigatória:

## [Manchete Interna H2 — ângulo principal da matéria]
Subtítulo informativo, sem clickbait, que abra um ângulo específico (não repetir o título).

**Lead jornalístico (1-2 parágrafos, ~120 palavras):**
Responda Quem? O quê? Quando? Onde? Por quê? em 4-6 frases.
Use pirâmide invertida — o essencial vem primeiro.
O leitor deve entender a notícia completa apenas lendo este trecho.

## [H2 — Contexto e detalhes]
**3-4 parágrafos (~280-350 palavras)** desenvolvendo a notícia com dados PRESENTES NA FONTE.

Se a fonte mencionar termos técnicos, explique-os naturalmente (sem parecer didático):
- ETF: Fundo negociado em bolsa que replica o desempenho de um ativo
- Halving: Evento programado que reduz pela metade a recompensa de mineração
- DeFi: Ecossistema de finanças descentralizadas sem intermediários tradicionais
- Layer 2: Soluções de segunda camada para escalabilidade de blockchains
- Staking: Processo de bloquear criptomoedas para validar transações e receber recompensas

Adicione contexto histórico ou de mercado quando RELEVANTE e VERIFICÁVEL na fonte.

⚠️ Use APENAS dados que estão explicitamente na fonte. NÃO invente números, datas, percentuais.

## [H2 — Impacto no Brasil] (OBRIGATÓRIO)
**2-3 parágrafos (~220-280 palavras)** com ângulo brasileiro específico. Esta seção é o diferencial editorial — sem ela, o artigo é apenas tradução de conteúdo gringo (Google penaliza).

Aborde pelo menos UM destes ângulos (o que fizer mais sentido pra notícia):
- Regulação: como CVM, BCB, Lei 14.478/2022 (marco cripto BR), Receita Federal afetam ou são afetados.
- Mercado local: impacto em exchanges nacionais (Mercado Bitcoin, Foxbit, NovaDAX, BitPreço), liquidez em real, paridade BTC/BRL.
- Investidor BR: impacto fiscal (IN 1.888 da Receita), tributação de ganho de capital cripto, declaração de IR.
- Comparação: como o fato se compara a iniciativas/regulação brasileiras similares.

Se nenhum ângulo BR for aplicável, mencione brevemente por que e como o leitor brasileiro pode acompanhar o desenrolar.

## [H2 — Próximos passos / O que observar]
**1-2 parágrafos (~120-160 palavras)** de fechamento analítico (NÃO conclusivo robótico).

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
   → Use "{keyword}" 3-5 vezes (densidade natural) E variações como "criptomoeda" ou "cripto".

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
</validacao_obrigatoria>"""

    # System Prompt v3.0 - Estruturado com tags XML para melhor parsing
    SYSTEM_PROMPT = """<persona>
Você é o Editor-Chefe do portal VerticeCripto, um veículo jornalístico especializado em criptoeconomia para o público brasileiro. Sua formação combina jornalismo financeiro (Bloomberg), tecnologia acessível (The Verge) e expertise no mercado cripto.
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
   - NUNCA invente preços, porcentagens, datas, valores ou estatísticas que NÃO estejam EXPLICITAMENTE na fonte fornecida OU na seção <dados_de_mercado>.
   - A seção <dados_de_mercado>, quando presente, contém dados VERIFICADOS de mercado em tempo real. Pode e DEVE citá-los quando forem pertinentes ao fato noticiado, sempre deixando claro que são dados de mercado do momento.
   - Se a fonte disser "Bitcoin subiu" e não houver <dados_de_mercado>, NÃO escreva "Bitcoin subiu 5,3%" ou "atingiu US$ 70.000".
   - Sem dados específicos, use termos como "registrou alta", "apresentou valorização", "sofreu queda".

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
- H2 (##) para CADA subtítulo de seção — o artigo tem MÚLTIPLOS H2 (ver estrutura), nunca um só
- **Negrito** para conceitos-chave e dados importantes
- Listas com hífen (-) quando houver 3+ itens relacionados
- Quebras de linha duplas (\\n\\n) entre TODOS os parágrafos
- Parágrafos com 2-4 frases cada (evite blocos muito longos)
- Alterne frases curtas e longas para ritmo natural
</formato_de_saida>

<requisitos_criticos>
⚠️ REQUISITOS DE VALIDAÇÃO AUTOMÁTICA - O artigo será REJEITADO se não cumprir:

1. MÍNIMO 700 PALAVRAS (IDEAL 900-1200): Artigos abaixo de 700 palavras são REJEITADOS e não rankeiam em nicho competitivo. Desenvolva cada seção com profundidade real (contexto, dados verificáveis, ângulo brasileiro), nunca com enchimento.
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
    
    async def generate_article(
        self,
        source_news: Dict,
        category: str = "default",
        correction_hint: Optional[str] = None,
    ) -> Optional[Dict]:
        """
        Gera um artigo completo a partir de uma notícia fonte (v3.0)

        Args:
            source_news: Notícia coletada das fontes
            category: Categoria do artigo para ajuste de tom (bitcoin, ethereum, defi, etc.)
            correction_hint: Hint opcional em retry — descreve falhas da geração
                anterior (ex.: word count baixo) para o LLM corrigir.

        Returns:
            Artigo gerado com título, conteúdo, excerpt e meta tags
        """
        try:
            title = source_news.get("title", "")
            # Preferir o texto completo extraído da matéria original
            # (ArticleExtractor); o resumo do RSS é o fallback — com 1-2
            # frases o LLM não tem material para 700+ palavras sem alucinar.
            description = source_news.get("full_text") or source_news.get("description", "")
            source = source_news.get("source", "")

            logger.info(f"Gerando artigo para: {title[:50]}... (categoria: {category})")

            dados = await self._generate_article_json(
                title,
                description,
                source,
                category,
                correction_hint,
                market_data=source_news.get("market_data"),
            )
            if not dados:
                logger.warning("Falha ao gerar artigo (JSON inaproveitável)")
                return None

            # A sanitização rodava dentro de _generate_content; agora incide
            # sobre o content_markdown que veio do JSON.
            content = self._sanitize_content(dados["content_markdown"])
            seo_title = dados["title"].strip()

            # Excerpt: o do LLM se estiver na faixa que o validador aceita
            # (80-200), senão derivado do conteúdo. Fora de faixa não pode
            # custar o descarte de um artigo já gerado.
            excerpt = (dados.get("excerpt") or "").strip()
            if not (self.MIN_EXCERPT_LENGTH <= len(excerpt) <= self.MAX_EXCERPT_LENGTH):
                if excerpt:
                    logger.warning(
                        f"Excerpt do LLM fora da faixa ({len(excerpt)} chars) — "
                        f"derivando do conteúdo"
                    )
                excerpt = await self._generate_excerpt(content)

            article = {
                "title": seo_title,
                "slug": slugify(seo_title),
                "content_markdown": content,
                "excerpt": excerpt,
                "meta_title": seo_title,
                "meta_description": (dados.get("meta_description") or "").strip() or None,
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

    def _build_article_prompt(
        self,
        title: str,
        description: str,
        source: str,
        category: str,
        keyword: str,
        correction_hint: Optional[str] = None,
        market_data: Optional[str] = None,
    ) -> str:
        """
        Monta o user prompt da chamada única.

        Reaproveita as seções que já existiam no prompt de conteúdo
        (<dados_da_fonte> até <validacao_obrigatoria>), acrescenta o contrato
        de saída no lugar do <output> antigo — que pedia "APENAS o artigo em
        Markdown", incompatível com JSON — e anexa o bloco de correção em retry.

        `market_data` entra logo após <dados_da_fonte>: é material de fonte, e
        fica antes das instruções de tarefa.
        """
        cat_config = self._get_category_config(category)
        base = self._ARTICLE_PROMPT_TEMPLATE.format(
            title=title,
            description=description,
            category=category,
            tom=cat_config["tom"],
            foco=cat_config["foco"],
            keyword=keyword,
        )

        if market_data:
            marcador = "</dados_da_fonte>"
            base = base.replace(
                marcador,
                marcador + "\n" + self.MARKET_DATA_BLOCK.format(market_data=market_data),
                1,
            )

        prompt = base + self.JSON_CONTRACT_BLOCK.format(keyword=keyword)

        if correction_hint:
            prompt += (
                "\n\n<correcao_obrigatoria>\n"
                "A geração anterior foi REPROVADA na validação editorial com estes problemas:\n"
                f"{correction_hint}\n\n"
                "Corrija TODOS esses problemas na nova geração. Se o problema foi "
                "word count abaixo do mínimo, EXPANDA as seções com mais contexto "
                "VERIFICÁVEL (regulação BR, dados on-chain, comparação histórica) — "
                "nunca com enchimento ou frases robóticas.\n"
                "</correcao_obrigatoria>"
            )
        return prompt

    async def _generate_article_json(
        self,
        title: str,
        description: str,
        source: str,
        category: str = "default",
        correction_hint: Optional[str] = None,
        market_data: Optional[str] = None,
    ) -> Optional[Dict]:
        """
        Gera o artigo completo — conteúdo, título, excerpt e meta — numa
        chamada só.

        Antes eram três chamadas sequenciais, e uma falha na segunda descartava
        o artigo junto com a chamada de conteúdo já paga. Aqui é transação
        única: ou vem tudo, ou não vem nada.

        O contrato JSON vive no PROMPT, não no mecanismo de saída estruturada
        de cada provedor: Gemini e OpenAI têm mecanismos diferentes, e apostar
        neles exigiria duas implementações de contrato. Cada provedor recebe
        apenas sua dica nativa de "responda JSON" como reforço barato.
        """
        cat_config = self._get_category_config(category)
        keyword = cat_config["keywords"][0] if cat_config["keywords"] else "criptomoeda"

        user_prompt = self._build_article_prompt(
            title, description, source, category, keyword, correction_hint, market_data
        )
        full_prompt = f"{self.SYSTEM_PROMPT}\n\n{user_prompt}"

        # Gemini primário
        if self.use_gemini and self.gemini_client:
            try:
                logger.info(f"[Gemini] Gerando artigo (chamada única) com {self.GEMINI_MODEL}...")
                response = await self.gemini_client.aio.models.generate_content(
                    model=self.GEMINI_MODEL,
                    contents=full_prompt,
                    config=genai.types.GenerateContentConfig(
                        temperature=0.4,
                        response_mime_type="application/json",
                    ),
                )
                artigo = self._parse_article_json(getattr(response, "text", None))
                if artigo:
                    return artigo
                logger.warning("[Gemini] JSON inaproveitável. Tentando OpenAI...")
            except Exception as e:
                logger.warning(f"[Gemini] Falha: {e}. Tentando OpenAI...")

        # Fallback OpenAI, mesmo contrato
        try:
            logger.info(f"[OpenAI] Gerando artigo (chamada única) com {self.OPENAI_MODEL}...")
            response = await self.openai_client.chat.completions.create(
                model=self.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.4,
                max_tokens=4000,
                response_format={"type": "json_object"},
            )
            return self._parse_article_json(response.choices[0].message.content)
        except Exception as e:
            logger.error(f"[OpenAI] Falha na geração: {e}")
            return None

    def _parse_article_json(self, text: Optional[str]) -> Optional[Dict]:
        """
        Parseia o JSON do artigo devolvido pelo LLM.

        Duas defesas, nesta ordem:
        1. Remoção de cercas ```json — modelos embrulham mesmo quando o prompt
           pede JSON puro.
        2. json_repair quando json.loads falha. O caso comum é aspas ou
           newlines não escapadas dentro do content_markdown longo; o repair
           conserta sem desfigurar conteúdo válido.

        Devolve None quando não há JSON aproveitável ou quando falta campo
        obrigatório (REQUIRED_ARTICLE_FIELDS).
        """
        if not text:
            return None

        limpo = text.strip()
        if limpo.startswith("```"):
            partes = limpo.split("```")
            limpo = partes[1] if len(partes) > 1 else limpo
            if limpo.startswith("json"):
                limpo = limpo[4:]
            limpo = limpo.strip()

        dados = None
        try:
            dados = json.loads(limpo)
        except (json.JSONDecodeError, ValueError):
            try:
                dados = json_repair.loads(limpo)
            except Exception as e:
                logger.error(f"[JSON] Parse falhou mesmo com json_repair: {e}")
                return None

        if not isinstance(dados, dict):
            logger.error(f"[JSON] Esperado objeto, recebido {type(dados).__name__}")
            return None

        for campo in self.REQUIRED_ARTICLE_FIELDS:
            valor = dados.get(campo)
            if not isinstance(valor, str) or not valor.strip():
                logger.error(f"[JSON] Campo obrigatório ausente ou vazio: {campo}")
                return None

        return dados

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

        # A lista de veículos agora é o atributo de classe SOURCE_SITE_NAMES.

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
        # Todo casamento usa \b...\b. Com substring, "decrypted" casava em
        # "decrypt" e "the blockchain" em "the block" — corrompendo o texto
        # ("the blockchain" virava "chain") e emitindo alerta CRÍTICO falso.
        # NÃO usar (?i) embutido: ele ignora `flags` e quebraria a exceção
        # case-sensitive de The Block.
        for site_name in self.SOURCE_SITE_NAMES:
            flags = (
                0 if site_name in self.CASE_SENSITIVE_SITE_NAMES else re.IGNORECASE
            )
            padrao_nome = rf'\b{re.escape(site_name)}\b'

            if not re.search(padrao_nome, result, flags):
                continue

            logger.error(
                f"[Sanitização CRÍTICA] LLM violou regra e citou veículo '{site_name}'. "
                f"Removendo frase atributiva. Revisar prompt se reincidir."
            )
            # Remover frase introdutória completa: "Segundo o CoinDesk, ..."
            result = re.sub(
                rf'\b(segundo|de acordo com|conforme|para|por)\s+(o|a|o portal|o site)?\s*{re.escape(site_name)}\b\s*[,.]?\s*',
                '',
                result,
                flags=flags,
            )
            # Remover construções "o CoinDesk informou/reportou/publicou X" -> "X"
            result = re.sub(
                rf'\b(o|a|o portal|o site)?\s*{re.escape(site_name)}\s+(informou|reportou|publicou|divulgou|noticiou|revelou)\s+que\s+',
                '',
                result,
                flags=flags,
            )
            # Remoção final: qualquer ocorrência restante do nome. Sem guarda
            # de `if`: re.sub não faz nada quando não há casamento.
            result = re.sub(padrao_nome, '', result, flags=flags)

        # Limpar artefatos de remoção (espaços duplos, vírgulas órfãs).
        # Restrito a [ \t] para NÃO colapsar \n\n — o validador exige quebras
        # duplas entre parágrafos (quality_validator._validate_content_structure).
        result = re.sub(r'[ \t]{2,}', ' ', result)
        result = re.sub(r'[ \t]+([,.;:])', r'\1', result)
        result = re.sub(r'([,.;:])[ \t]*\1+', r'\1', result)

        return result.strip()
    
    async def _generate_excerpt(self, content: str) -> Optional[str]:
        """
        Gera excerpt a partir do primeiro parágrafo de TEXTO do artigo.
        Linhas de heading são ignoradas — sem isso o texto do primeiro H2
        vazava colado na primeira frase do excerpt.
        """
        paragraphs = [
            line.strip()
            for line in content.split('\n')
            if line.strip() and not line.strip().startswith('#')
        ]
        text = ' '.join(paragraphs).replace('**', '').replace('*', '')

        sentences = text.split('. ')[:2]
        excerpt = '. '.join(sentences)

        # Limitar a 150 caracteres
        if len(excerpt) > 150:
            excerpt = excerpt[:147] + "..."

        return excerpt
    
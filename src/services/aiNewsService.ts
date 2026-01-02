import { env } from "@config/env";

interface AIGeneratedNews {
  title: string;
  content: string;
  excerpt: string;
  tags: string[];
}

/**
 * AI News Service
 * Generates news articles using OpenAI GPT-4
 */
export class AINewsService {
  /**
   * Generate news article using GPT-4
   */
  static async generateNewsArticle(
    topic: string,
    category: string
  ): Promise<AIGeneratedNews> {
    if (!env.OPENAI_API_KEY) {
      throw new Error("OpenAI API key not configured");
    }

    try {
      const response = await fetch("https://api.openai.com/v1/chat/completions", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${env.OPENAI_API_KEY}`,
        },
        body: JSON.stringify({
          model: "gpt-4",
          messages: [
            {
              role: "system",
              content: `Você é um jornalista especializado em criptomoedas e blockchain. 
Crie artigos informativos, bem estruturados e precisos sobre ${category}.
Sempre cite fontes quando apropriado e mantenha um tom profissional.
Responda em JSON com os campos: title, content (mínimo 500 palavras), excerpt (máximo 150 palavras), tags (array de strings).`,
            },
            {
              role: "user",
              content: `Gere um artigo de notícia sobre: ${topic}`,
            },
          ],
          temperature: 0.7,
          max_tokens: 2000,
        }),
      });

      if (!response.ok) {
        throw new Error(`OpenAI API error: ${response.statusText}`);
      }

      const data = await response.json() as any;
      const content = data.choices[0].message.content;

      // Parse JSON response from GPT
      const parsed = JSON.parse(content) as AIGeneratedNews;

      return {
        title: parsed.title,
        content: parsed.content,
        excerpt: parsed.excerpt,
        tags: parsed.tags || [],
      };
    } catch (error) {
      console.error("AI news generation error:", error);
      throw new Error("Failed to generate news article");
    }
  }

  /**
   * Generate multiple news articles
   */
  static async generateMultipleArticles(
    topics: Array<{ topic: string; category: string }>,
    concurrency: number = 3
  ): Promise<AIGeneratedNews[]> {
    const results: AIGeneratedNews[] = [];

    // Process topics with concurrency limit
    for (let i = 0; i < topics.length; i += concurrency) {
      const batch = topics.slice(i, i + concurrency);
      const batchResults = await Promise.all(
        batch.map((item) =>
          this.generateNewsArticle(item.topic, item.category).catch((err) => {
            console.error(`Failed to generate article for ${item.topic}:`, err);
            return null;
          })
        )
      );

      results.push(...batchResults.filter((r) => r !== null) as AIGeneratedNews[]);
    }

    return results;
  }

  /**
   * Get trending topics for news generation
   */
  static getTrendingTopics(): Array<{ topic: string; category: string }> {
    return [
      { topic: "Bitcoin alcança novo patamar de preço", category: "Bitcoin" },
      { topic: "Ethereum atualiza protocolo com melhorias", category: "Ethereum" },
      { topic: "Novo protocolo DeFi revoluciona empréstimos", category: "DeFi" },
      { topic: "Regulação cripto avança em novo país", category: "Regulação" },
      { topic: "NFT marketplace quebra recorde de volume", category: "NFT" },
      { topic: "Altcoin promissora ganha tração no mercado", category: "Altcoins" },
      { topic: "Análise técnica: Bitcoin em tendência de alta", category: "Mercado" },
      { topic: "Inovação em segurança blockchain", category: "Tecnologia" },
    ];
  }
}

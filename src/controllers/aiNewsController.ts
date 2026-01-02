import { Request, Response } from "express";
import { AINewsService } from "@services/aiNewsService";
import { ArticleService } from "@services/articleService";
import { asyncHandler, AppError } from "@middlewares/errorHandler";

export class AINewsController {
  /**
   * POST /api/ai/generate-article
   * Generate a single article using AI (admin only)
   */
  static generateArticle = asyncHandler(async (req: Request, res: Response) => {
    if (!req.user || req.user.role !== "admin") {
      throw new AppError(403, "Only admins can generate articles");
    }

    const { topic, categoryId } = req.body;

    if (!topic || !categoryId) {
      throw new AppError(400, "Topic and categoryId are required");
    }

    try {
      // Generate article using AI
      const aiContent = await AINewsService.generateNewsArticle(topic, categoryId);

      // Create article in database
      const article = await ArticleService.createArticle({
        title: aiContent.title,
        content: aiContent.content,
        excerpt: aiContent.excerpt,
        categoryId,
        authorId: req.user.id,
        isAIGenerated: true,
        tags: aiContent.tags,
      });

      res.status(201).json({
        success: true,
        data: { article },
      });
    } catch (error) {
      console.error("AI article generation error:", error);
      throw new AppError(500, "Failed to generate article");
    }
  });

  /**
   * POST /api/ai/generate-batch
   * Generate multiple articles using AI (admin only)
   */
  static generateBatch = asyncHandler(async (req: Request, res: Response) => {
    if (!req.user || req.user.role !== "admin") {
      throw new AppError(403, "Only admins can generate articles");
    }

    const { count = 5, concurrency = 2 } = req.body;

    if (count > 10) {
      throw new AppError(400, "Maximum 10 articles per batch");
    }

    try {
      // Get trending topics
      const topics = AINewsService.getTrendingTopics().slice(0, count);

      // Generate articles using AI
      const aiArticles = await AINewsService.generateMultipleArticles(
        topics,
        concurrency
      );

      // Create articles in database
      const createdArticles = await Promise.all(
        aiArticles.map((aiContent) =>
          ArticleService.createArticle({
            title: aiContent.title,
            content: aiContent.content,
            excerpt: aiContent.excerpt,
            categoryId: topics.find((t) => t.topic === aiContent.title)
              ?.category || "general",
            authorId: req.user!.id,
            isAIGenerated: true,
            tags: aiContent.tags,
          })
        )
      );

      res.status(201).json({
        success: true,
        data: {
          articles: createdArticles,
          count: createdArticles.length,
        },
      });
    } catch (error) {
      console.error("Batch article generation error:", error);
      throw new AppError(500, "Failed to generate articles");
    }
  });

  /**
   * GET /api/ai/trending-topics
   * Get trending topics for news generation (admin only)
   */
  static getTrendingTopics = asyncHandler(async (req: Request, res: Response) => {
    if (!req.user || req.user.role !== "admin") {
      throw new AppError(403, "Only admins can view trending topics");
    }

    const topics = AINewsService.getTrendingTopics();

    res.json({
      success: true,
      data: { topics },
    });
  });
}

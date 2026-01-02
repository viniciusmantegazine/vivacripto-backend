import { Request, Response } from "express";
import { ArticleService } from "@services/articleService";
import { asyncHandler, AppError } from "@middlewares/errorHandler";

export class ArticleController {
  /**
   * POST /api/articles
   * Create a new article (admin only)
   */
  static createArticle = asyncHandler(async (req: Request, res: Response) => {
    if (!req.user || req.user.role !== "admin") {
      throw new AppError(403, "Only admins can create articles");
    }

    const { title, content, excerpt, imageUrl, categoryId, tags } = req.body;

    if (!title || !content || !categoryId) {
      throw new AppError(400, "Title, content, and categoryId are required");
    }

    const article = await ArticleService.createArticle({
      title,
      content,
      excerpt,
      imageUrl,
      categoryId,
      authorId: req.user.id,
      tags,
    });

    res.status(201).json({
      success: true,
      data: { article },
    });
  });

  /**
   * GET /api/articles
   * Get all articles with filters
   */
  static getArticles = asyncHandler(async (req: Request, res: Response) => {
    const { categoryId, isPublished, limit = 10, offset = 0 } = req.query;

    const articles = await ArticleService.getArticles({
      categoryId: categoryId as string,
      isPublished: isPublished === "true",
      limit: parseInt(limit as string),
      offset: parseInt(offset as string),
    });

    const total = await ArticleService.getArticleCount({
      categoryId: categoryId as string,
      isPublished: isPublished === "true",
    });

    res.json({
      success: true,
      data: {
        articles,
        total,
        limit: parseInt(limit as string),
        offset: parseInt(offset as string),
      },
    });
  });

  /**
   * GET /api/articles/:id
   * Get article by ID
   */
  static getArticleById = asyncHandler(async (req: Request, res: Response) => {
    const { id } = req.params;

    const article = await ArticleService.getArticleById(id);

    if (!article) {
      throw new AppError(404, "Article not found");
    }

    // Increment views
    await ArticleService.incrementViews(id);

    res.json({
      success: true,
      data: { article },
    });
  });

  /**
   * PUT /api/articles/:id
   * Update article (admin only)
   */
  static updateArticle = asyncHandler(async (req: Request, res: Response) => {
    if (!req.user || req.user.role !== "admin") {
      throw new AppError(403, "Only admins can update articles");
    }

    const { id } = req.params;
    const { title, content, excerpt, imageUrl, categoryId } = req.body;

    const article = await ArticleService.updateArticle(id, {
      title,
      content,
      excerpt,
      imageUrl,
      categoryId,
    });

    if (!article) {
      throw new AppError(404, "Article not found");
    }

    res.json({
      success: true,
      data: { article },
    });
  });

  /**
   * POST /api/articles/:id/publish
   * Publish article (admin only)
   */
  static publishArticle = asyncHandler(async (req: Request, res: Response) => {
    if (!req.user || req.user.role !== "admin") {
      throw new AppError(403, "Only admins can publish articles");
    }

    const { id } = req.params;

    const article = await ArticleService.publishArticle(id);

    if (!article) {
      throw new AppError(404, "Article not found");
    }

    res.json({
      success: true,
      data: { article },
    });
  });

  /**
   * DELETE /api/articles/:id
   * Delete article (admin only)
   */
  static deleteArticle = asyncHandler(async (req: Request, res: Response) => {
    if (!req.user || req.user.role !== "admin") {
      throw new AppError(403, "Only admins can delete articles");
    }

    const { id } = req.params;

    const success = await ArticleService.deleteArticle(id);

    if (!success) {
      throw new AppError(404, "Article not found");
    }

    res.json({
      success: true,
      message: "Article deleted successfully",
    });
  });
}

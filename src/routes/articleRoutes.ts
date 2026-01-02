import { Router } from "express";
import { ArticleController } from "@controllers/articleController";
import { CategoryController } from "@controllers/categoryController";
import { AINewsController } from "@controllers/aiNewsController";
import { authMiddleware, optionalAuthMiddleware } from "@middlewares/auth";

const router = Router();

/**
 * Article Routes
 */

// GET /api/articles - Get all articles (public)
router.get("/", optionalAuthMiddleware, ArticleController.getArticles);

// POST /api/articles - Create article (admin only)
router.post("/", authMiddleware, ArticleController.createArticle);

// GET /api/articles/:id - Get article by ID (public)
router.get("/:id", ArticleController.getArticleById);

// PUT /api/articles/:id - Update article (admin only)
router.put("/:id", authMiddleware, ArticleController.updateArticle);

// POST /api/articles/:id/publish - Publish article (admin only)
router.post("/:id/publish", authMiddleware, ArticleController.publishArticle);

// DELETE /api/articles/:id - Delete article (admin only)
router.delete("/:id", authMiddleware, ArticleController.deleteArticle);

/**
 * Category Routes
 */

// GET /api/categories - Get all categories (public)
router.get("/categories", CategoryController.getCategories);

// POST /api/categories - Create category (admin only)
router.post("/categories", authMiddleware, CategoryController.createCategory);

// GET /api/categories/:id - Get category by ID (public)
router.get("/categories/:id", CategoryController.getCategoryById);

// PUT /api/categories/:id - Update category (admin only)
router.put("/categories/:id", authMiddleware, CategoryController.updateCategory);

// DELETE /api/categories/:id - Delete category (admin only)
router.delete("/categories/:id", authMiddleware, CategoryController.deleteCategory);

/**
 * AI News Routes
 */

// POST /api/ai/generate-article - Generate single article (admin only)
router.post("/ai/generate-article", authMiddleware, AINewsController.generateArticle);

// POST /api/ai/generate-batch - Generate multiple articles (admin only)
router.post("/ai/generate-batch", authMiddleware, AINewsController.generateBatch);

// GET /api/ai/trending-topics - Get trending topics (admin only)
router.get("/ai/trending-topics", authMiddleware, AINewsController.getTrendingTopics);

export default router;

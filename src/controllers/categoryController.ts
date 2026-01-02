import { Request, Response } from "express";
import { CategoryService } from "@services/categoryService";
import { asyncHandler, AppError } from "@middlewares/errorHandler";

export class CategoryController {
  /**
   * POST /api/categories
   * Create a new category (admin only)
   */
  static createCategory = asyncHandler(async (req: Request, res: Response) => {
    if (!req.user || req.user.role !== "admin") {
      throw new AppError(403, "Only admins can create categories");
    }

    const { name, description, color, icon } = req.body;

    if (!name) {
      throw new AppError(400, "Category name is required");
    }

    const category = await CategoryService.createCategory({
      name,
      description,
      color,
      icon,
    });

    res.status(201).json({
      success: true,
      data: { category },
    });
  });

  /**
   * GET /api/categories
   * Get all categories
   */
  static getCategories = asyncHandler(async (req: Request, res: Response) => {
    const categories = await CategoryService.getCategories({
      isActive: true,
    });

    res.json({
      success: true,
      data: { categories },
    });
  });

  /**
   * GET /api/categories/:id
   * Get category by ID
   */
  static getCategoryById = asyncHandler(async (req: Request, res: Response) => {
    const { id } = req.params;

    const category = await CategoryService.getCategoryById(id);

    if (!category) {
      throw new AppError(404, "Category not found");
    }

    res.json({
      success: true,
      data: { category },
    });
  });

  /**
   * PUT /api/categories/:id
   * Update category (admin only)
   */
  static updateCategory = asyncHandler(async (req: Request, res: Response) => {
    if (!req.user || req.user.role !== "admin") {
      throw new AppError(403, "Only admins can update categories");
    }

    const { id } = req.params;
    const { name, description, color, icon, isActive } = req.body;

    const category = await CategoryService.updateCategory(id, {
      name,
      description,
      color,
      icon,
      isActive,
    });

    if (!category) {
      throw new AppError(404, "Category not found");
    }

    res.json({
      success: true,
      data: { category },
    });
  });

  /**
   * DELETE /api/categories/:id
   * Delete category (admin only)
   */
  static deleteCategory = asyncHandler(async (req: Request, res: Response) => {
    if (!req.user || req.user.role !== "admin") {
      throw new AppError(403, "Only admins can delete categories");
    }

    const { id } = req.params;

    const success = await CategoryService.deleteCategory(id);

    if (!success) {
      throw new AppError(404, "Category not found");
    }

    res.json({
      success: true,
      message: "Category deleted successfully",
    });
  });
}

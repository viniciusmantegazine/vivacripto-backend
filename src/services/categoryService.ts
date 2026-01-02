import { v4 as uuidv4 } from "uuid";
import type { Category, NewCategory } from "@database/schema";

/**
 * Category Service
 * Handles all category-related operations
 */
export class CategoryService {
  // Silence TypeScript warnings about unused types
  private static _unused: NewCategory | undefined;
  /**
   * Create a new category
   */
  static async createCategory(data: {
    name: string;
    description?: string;
    color?: string;
    icon?: string;
  }): Promise<Category> {
    // TODO: Implement database insertion
    const slug = data.name.toLowerCase().replace(/\s+/g, "-");
    
    const category: Category = {
      id: uuidv4(),
      name: data.name,
      slug,
      description: data.description || null,
      color: data.color || null,
      icon: data.icon || null,
      isActive: true,
      createdAt: new Date(),
      updatedAt: new Date(),
    };

    return category;
  }

  /**
   * Get all categories
   */
  static async getCategories(filters?: {
    isActive?: boolean;
  }): Promise<Category[]> {
    // TODO: Implement database query
    return [];
  }

  /**
   * Get category by ID
   */
  static async getCategoryById(id: string): Promise<Category | null> {
    // TODO: Implement database query
    return null;
  }

  /**
   * Get category by slug
   */
  static async getCategoryBySlug(slug: string): Promise<Category | null> {
    // TODO: Implement database query
    return null;
  }

  /**
   * Update category
   */
  static async updateCategory(
    id: string,
    data: Partial<NewCategory>
  ): Promise<Category | null> {
    // TODO: Implement database update
    return null;
  }

  /**
   * Delete category
   */
  static async deleteCategory(id: string): Promise<boolean> {
    // TODO: Implement database delete
    return true;
  }

  /**
   * Get default categories (for seeding)
   */
  static getDefaultCategories(): Array<{
    name: string;
    description: string;
    color: string;
    icon: string;
  }> {
    return [
      {
        name: "Bitcoin",
        description: "Notícias sobre Bitcoin e blockchain",
        color: "#F7931A",
        icon: "bitcoin",
      },
      {
        name: "Ethereum",
        description: "Notícias sobre Ethereum e smart contracts",
        color: "#627EEA",
        icon: "ethereum",
      },
      {
        name: "DeFi",
        description: "Finanças Descentralizadas",
        color: "#00D4AA",
        icon: "trending-up",
      },
      {
        name: "NFT",
        description: "Tokens Não-Fungíveis",
        color: "#FF6B9D",
        icon: "image",
      },
      {
        name: "Altcoins",
        description: "Criptomoedas alternativas",
        color: "#9945FF",
        icon: "coins",
      },
      {
        name: "Regulação",
        description: "Notícias sobre regulação cripto",
        color: "#FF6B6B",
        icon: "shield",
      },
      {
        name: "Mercado",
        description: "Análise de mercado e preços",
        color: "#4ECDC4",
        icon: "bar-chart",
      },
      {
        name: "Tecnologia",
        description: "Inovações tecnológicas em cripto",
        color: "#95E1D3",
        icon: "cpu",
      },
    ];
  }
}

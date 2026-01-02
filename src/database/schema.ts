import {
  mysqlTable,
  varchar,
  text,
  timestamp,
  boolean,
  int,
} from "drizzle-orm/mysql-core";
import { sql } from "drizzle-orm";

/**
 * Users Table
 */
export const users = mysqlTable("users", {
  id: varchar("id", { length: 255 }).primaryKey(),
  email: varchar("email", { length: 255 }).notNull().unique(),
  name: varchar("name", { length: 255 }).notNull(),
  picture: text("picture"),
  googleId: varchar("google_id", { length: 255 }).unique(),
  role: varchar("role", { length: 20 }).default("user"),
  isActive: boolean("is_active").default(true),
  createdAt: timestamp("created_at").default(sql`CURRENT_TIMESTAMP`),
  updatedAt: timestamp("updated_at").default(sql`CURRENT_TIMESTAMP`).onUpdateNow(),
});

/**
 * Categories Table
 */
export const categories = mysqlTable("categories", {
  id: varchar("id", { length: 255 }).primaryKey(),
  name: varchar("name", { length: 255 }).notNull().unique(),
  slug: varchar("slug", { length: 255 }).notNull().unique(),
  description: text("description"),
  color: varchar("color", { length: 7 }),
  icon: varchar("icon", { length: 255 }),
  isActive: boolean("is_active").default(true),
  createdAt: timestamp("created_at").default(sql`CURRENT_TIMESTAMP`),
  updatedAt: timestamp("updated_at").default(sql`CURRENT_TIMESTAMP`).onUpdateNow(),
});

/**
 * News Articles Table
 */
export const articles = mysqlTable("articles", {
  id: varchar("id", { length: 255 }).primaryKey(),
  title: varchar("title", { length: 255 }).notNull(),
  slug: varchar("slug", { length: 255 }).notNull().unique(),
  content: text("content").notNull(),
  excerpt: text("excerpt"),
  imageUrl: text("image_url"),
  categoryId: varchar("category_id", { length: 255 }).notNull(),
  authorId: varchar("author_id", { length: 255 }).notNull(),
  isAIGenerated: boolean("is_ai_generated").default(false),
  isPublished: boolean("is_published").default(false),
  publishedAt: timestamp("published_at"),
  views: int("views").default(0),
  createdAt: timestamp("created_at").default(sql`CURRENT_TIMESTAMP`),
  updatedAt: timestamp("updated_at").default(sql`CURRENT_TIMESTAMP`).onUpdateNow(),
});

/**
 * Article Tags (many-to-many relationship)
 */
export const articleTags = mysqlTable("article_tags", {
  id: varchar("id", { length: 255 }).primaryKey(),
  articleId: varchar("article_id", { length: 255 }).notNull(),
  tag: varchar("tag", { length: 100 }).notNull(),
  createdAt: timestamp("created_at").default(sql`CURRENT_TIMESTAMP`),
});

/**
 * Types for TypeScript
 */
export type User = typeof users.$inferSelect & { role?: "user" | "admin" };
export type NewUser = typeof users.$inferInsert;

export type Category = typeof categories.$inferSelect;
export type NewCategory = typeof categories.$inferInsert;

export type Article = typeof articles.$inferSelect;
export type NewArticle = typeof articles.$inferInsert;

export type ArticleTag = typeof articleTags.$inferSelect;
export type NewArticleTag = typeof articleTags.$inferInsert;

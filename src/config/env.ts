import dotenv from "dotenv";

dotenv.config();

export const env = {
  // Server
  PORT: parseInt(process.env.PORT || "3000", 10),
  NODE_ENV: process.env.NODE_ENV || "development",
  API_URL: process.env.API_URL || "http://localhost:3000",
  FRONTEND_URL: process.env.FRONTEND_URL || "http://localhost:5173",

  // Database
  DATABASE_URL: process.env.DATABASE_URL || "",

  // Google OAuth
  GOOGLE_CLIENT_ID: process.env.GOOGLE_CLIENT_ID || "",
  GOOGLE_CLIENT_SECRET: process.env.GOOGLE_CLIENT_SECRET || "",
  GOOGLE_CALLBACK_URL: process.env.GOOGLE_CALLBACK_URL || "",

  // JWT
  JWT_SECRET: process.env.JWT_SECRET || "",
  JWT_EXPIRY: process.env.JWT_EXPIRY || "7d",

  // OpenAI
  OPENAI_API_KEY: process.env.OPENAI_API_KEY || "",

  // AWS S3
  AWS_ACCESS_KEY_ID: process.env.AWS_ACCESS_KEY_ID || "",
  AWS_SECRET_ACCESS_KEY: process.env.AWS_SECRET_ACCESS_KEY || "",
  AWS_REGION: process.env.AWS_REGION || "us-east-1",
  AWS_S3_BUCKET: process.env.AWS_S3_BUCKET || "",
  AWS_S3_ENDPOINT: process.env.AWS_S3_ENDPOINT || "",
  AWS_S3_PUBLIC_URL: process.env.AWS_S3_PUBLIC_URL || "",

  // Email
  SENDGRID_API_KEY: process.env.SENDGRID_API_KEY || "",

  // Logging
  LOG_LEVEL: process.env.LOG_LEVEL || "info",
};

// Validate required environment variables
const requiredEnvs = [
  "DATABASE_URL",
  "GOOGLE_CLIENT_ID",
  "GOOGLE_CLIENT_SECRET",
  "JWT_SECRET",
];

for (const envVar of requiredEnvs) {
  if (!process.env[envVar]) {
    console.warn(`⚠️  Missing environment variable: ${envVar}`);
  }
}

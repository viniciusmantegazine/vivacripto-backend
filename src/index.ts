import express from "express";
import cors from "cors";
import { env } from "@config/env";
import { errorHandler } from "@middlewares/errorHandler";
import authRoutes from "@routes/authRoutes";
import articleRoutes from "@routes/articleRoutes";

const app = express();

/**
 * CORS Configuration
 * Normalize frontend URL to handle trailing slashes
 */
const getFrontendUrl = (): string => {
  const url = env.FRONTEND_URL || "http://localhost:5173";
  return url.replace(/\/$/, ""); // Remove trailing slash
};

/**
 * Middleware
 */
app.use(
  cors({
    origin: (origin, callback) => {
      // Allow requests from the frontend URL (with or without trailing slash)
      const frontendUrl = getFrontendUrl();
      
      if (!origin || origin === frontendUrl || origin === `${frontendUrl}/`) {
        callback(null, true);
      } else if (env.NODE_ENV === "development") {
        // Allow any origin in development
        callback(null, true);
      } else {
        callback(new Error("Not allowed by CORS"));
      }
    },
    credentials: true,
    methods: ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allowedHeaders: ["Content-Type", "Authorization"],
    optionsSuccessStatus: 200,
  })
);

app.use(express.json());
app.use(express.urlencoded({ extended: true }));

/**
 * Health check
 */
app.get("/health", (req, res) => {
  res.json({
    success: true,
    message: "VivaCripto Backend is running",
    timestamp: new Date().toISOString(),
  });
});

/**
 * Routes
 */
app.use("/api/auth", authRoutes);
app.use("/api/articles", articleRoutes);

/**
 * 404 handler
 */
app.use((req, res) => {
  res.status(404).json({
    success: false,
    error: "Route not found",
  });
});

/**
 * Error handler (must be last)
 */
app.use(errorHandler);

/**
 * Start server
 */
const PORT = env.PORT;
app.listen(PORT, () => {
  console.log(`🚀 VivaCripto Backend running on http://localhost:${PORT}`);
  console.log(`📝 Environment: ${env.NODE_ENV}`);
  console.log(`🔐 Google OAuth configured: ${!!env.GOOGLE_CLIENT_ID}`);
  console.log(`🌐 CORS enabled for: ${getFrontendUrl()}`);
});

export default app;

import express from "express";
import cors from "cors";
import { env } from "@config/env";
import { errorHandler } from "@middlewares/errorHandler";
import authRoutes from "@routes/authRoutes";

const app = express();

/**
 * Middleware
 */
app.use(
  cors({
    origin: env.FRONTEND_URL,
    credentials: true,
    methods: ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allowedHeaders: ["Content-Type", "Authorization"],
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
});

export default app;

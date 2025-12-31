import { Router } from "express";
import { AuthController } from "@controllers/authController";
import { authMiddleware } from "@middlewares/auth";

const router = Router();

/**
 * Public routes
 */

// GET /api/auth/google - Get Google OAuth URL
router.get("/google", AuthController.getGoogleAuthUrl);

// POST /api/auth/google/callback - Handle Google OAuth callback
router.post("/google/callback", AuthController.googleCallback);

// POST /api/auth/verify-token - Verify JWT token
router.post("/verify-token", AuthController.verifyToken);

// POST /api/auth/logout - Logout
router.post("/logout", AuthController.logout);

/**
 * Protected routes
 */

// GET /api/auth/me - Get current user
router.get("/me", authMiddleware, AuthController.getCurrentUser);

export default router;

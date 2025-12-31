import { Request, Response } from "express";
import { AuthService } from "@services/authService";
import { asyncHandler, AppError } from "@middlewares/errorHandler";

export class AuthController {
  /**
   * GET /api/auth/google
   * Redirect to Google OAuth login
   */
  static getGoogleAuthUrl = asyncHandler(
    async (req: Request, res: Response) => {
      const url = AuthService.getGoogleAuthUrl();
      res.json({
        success: true,
        data: {
          url,
        },
      });
    }
  );

  /**
   * POST /api/auth/google/callback
   * Handle Google OAuth callback
   */
  static googleCallback = asyncHandler(async (req: Request, res: Response) => {
    const { code } = req.body;

    if (!code) {
      throw new AppError(400, "Authorization code is required");
    }

    try {
      // Exchange code for tokens
      const tokens = await AuthService.exchangeCodeForTokens(code);

      if (!tokens.id_token) {
        throw new AppError(400, "Failed to get ID token from Google");
      }

      // Verify and decode the ID token
      const googleUser = await AuthService.verifyGoogleToken(tokens.id_token);

      // TODO: In a real app, you would:
      // 1. Check if user exists in database
      // 2. If not, create a new user
      // 3. Update last login time
      // For now, we'll just create a mock user object

      const mockUser = {
        id: googleUser.id,
        email: googleUser.email,
        name: googleUser.name,
        picture: googleUser.picture,
        googleId: googleUser.id,
        createdAt: new Date(),
        updatedAt: new Date(),
      };

      // Generate JWT token
      const jwtToken = AuthService.generateToken(mockUser);

      res.json({
        success: true,
        data: {
          token: jwtToken,
          user: {
            id: mockUser.id,
            email: mockUser.email,
            name: mockUser.name,
            picture: mockUser.picture,
          },
        },
      });
    } catch (error) {
      console.error("Google callback error:", error);
      throw new AppError(400, "Failed to authenticate with Google");
    }
  });

  /**
   * POST /api/auth/verify-token
   * Verify if token is valid
   */
  static verifyToken = asyncHandler(async (req: Request, res: Response) => {
    const { token } = req.body;

    if (!token) {
      throw new AppError(400, "Token is required");
    }

    try {
      const decoded = AuthService.verifyToken(token);
      res.json({
        success: true,
        data: {
          valid: true,
          user: {
            id: decoded.userId,
            email: decoded.email,
          },
        },
      });
    } catch (error) {
      res.json({
        success: true,
        data: {
          valid: false,
        },
      });
    }
  });

  /**
   * POST /api/auth/logout
   * Logout user (client-side token deletion)
   */
  static logout = asyncHandler(async (req: Request, res: Response) => {
    // Token deletion happens on client side
    res.json({
      success: true,
      message: "Logged out successfully",
    });
  });

  /**
   * GET /api/auth/me
   * Get current user info
   */
  static getCurrentUser = asyncHandler(async (req: Request, res: Response) => {
    if (!req.user) {
      throw new AppError(401, "Not authenticated");
    }

    res.json({
      success: true,
      data: {
        user: {
          id: req.user.id,
          email: req.user.email,
          name: req.user.name,
          picture: req.user.picture,
        },
      },
    });
  });
}

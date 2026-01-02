import jwt from "jsonwebtoken";
import { OAuth2Client } from "google-auth-library";
import { env } from "@config/env";
import type { GoogleUser, AuthUser, JWTPayload } from "@types";

const googleClient = new OAuth2Client(
  env.GOOGLE_CLIENT_ID,
  env.GOOGLE_CLIENT_SECRET,
  env.GOOGLE_CALLBACK_URL
);

export class AuthService {
  /**
   * Verify Google ID Token
   */
  static async verifyGoogleToken(idToken: string): Promise<GoogleUser> {
    try {
      const ticket = await googleClient.verifyIdToken({
        idToken,
        audience: env.GOOGLE_CLIENT_ID,
      });

      const payload = ticket.getPayload();
      if (!payload) {
        throw new Error("Invalid token payload");
      }

      return {
        id: payload.sub,
        email: payload.email || "",
        name: payload.name || "",
        picture: payload.picture,
        email_verified: payload.email_verified,
      };
    } catch (error) {
      console.error("Google token verification failed:", error);
      throw new Error("Invalid Google token");
    }
  }

  /**
   * Generate JWT token
   */
  static generateToken(user: AuthUser): string {
    const payload: JWTPayload = {
      userId: user.id,
      email: user.email,
    };

    return jwt.sign(payload, env.JWT_SECRET, {
      expiresIn: env.JWT_EXPIRY as string | number,
    } as jwt.SignOptions);
  }

  /**
   * Verify JWT token
   */
  static verifyToken(token: string): JWTPayload {
    try {
      return jwt.verify(token, env.JWT_SECRET) as JWTPayload;
    } catch (error) {
      throw new Error("Invalid or expired token");
    }
  }

  /**
   * Get Google OAuth URL
   */
  static getGoogleAuthUrl(): string {
    const scopes = [
      "https://www.googleapis.com/auth/userinfo.email",
      "https://www.googleapis.com/auth/userinfo.profile",
    ];

    const url = googleClient.generateAuthUrl({
      access_type: "offline",
      scope: scopes,
      prompt: "consent",
    });

    return url;
  }

  /**
   * Exchange authorization code for tokens
   */
  static async exchangeCodeForTokens(code: string) {
    try {
      const { tokens } = await googleClient.getToken(code);
      return tokens;
    } catch (error) {
      console.error("Token exchange failed:", error);
      throw new Error("Failed to exchange authorization code");
    }
  }
}

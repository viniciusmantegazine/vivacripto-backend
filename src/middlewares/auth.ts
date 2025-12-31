import { Request, Response, NextFunction } from "express";
import jwt from "jsonwebtoken";
import { env } from "@config/env";
import { JWTPayload, AuthUser } from "@types/index";

declare global {
  namespace Express {
    interface Request {
      user?: AuthUser;
      token?: string;
    }
  }
}

export const authMiddleware = (
  req: Request,
  res: Response,
  next: NextFunction
) => {
  try {
    const token =
      req.headers.authorization?.replace("Bearer ", "") ||
      req.cookies?.token;

    if (!token) {
      return res.status(401).json({
        success: false,
        error: "No token provided",
      });
    }

    const decoded = jwt.verify(token, env.JWT_SECRET) as JWTPayload;
    req.token = token;
    // Note: In a real app, you'd fetch the user from the database here
    // For now, we'll just attach the decoded payload
    req.user = {
      id: decoded.userId,
      email: decoded.email,
      name: "",
      googleId: "",
      createdAt: new Date(),
      updatedAt: new Date(),
    };

    next();
  } catch (error) {
    return res.status(401).json({
      success: false,
      error: "Invalid token",
    });
  }
};

export const optionalAuthMiddleware = (
  req: Request,
  res: Response,
  next: NextFunction
) => {
  try {
    const token =
      req.headers.authorization?.replace("Bearer ", "") ||
      req.cookies?.token;

    if (token) {
      const decoded = jwt.verify(token, env.JWT_SECRET) as JWTPayload;
      req.token = token;
      req.user = {
        id: decoded.userId,
        email: decoded.email,
        name: "",
        googleId: "",
        createdAt: new Date(),
        updatedAt: new Date(),
      };
    }
  } catch (error) {
    // Silently fail - user is optional
  }

  next();
};

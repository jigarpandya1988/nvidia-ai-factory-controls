/**
 * JWT Authentication Middleware
 * ==============================
 * - POST /api/auth/login → returns JWT token
 * - Auth middleware checks Authorization: Bearer <token> on protected routes
 * - Role-based access control (admin, operator, viewer)
 */

import { FastifyInstance, FastifyRequest, FastifyReply } from 'fastify';
import { validateCredentials, hasPermission, UserRole } from './users';

// Simple JWT implementation (no external dependency for demo)
// In production, use @fastify/jwt or jsonwebtoken

const JWT_SECRET = 'aifactory-scada-secret-key-change-in-production';
const JWT_EXPIRY_HOURS = 8;

interface TokenPayload {
  username: string;
  role: UserRole;
  displayName: string;
  iat: number;
  exp: number;
}

/**
 * Base64url encode/decode helpers.
 */
function base64urlEncode(data: string): string {
  return Buffer.from(data).toString('base64url');
}

function base64urlDecode(data: string): string {
  return Buffer.from(data, 'base64url').toString('utf8');
}

/**
 * Simple HMAC-SHA256 signing (using Node crypto).
 */
function sign(payload: string, secret: string): string {
  const crypto = require('crypto');
  return crypto
    .createHmac('sha256', secret)
    .update(payload)
    .digest('base64url');
}

/**
 * Create a JWT token.
 */
function createToken(payload: Omit<TokenPayload, 'iat' | 'exp'>): string {
  const now = Math.floor(Date.now() / 1000);
  const fullPayload: TokenPayload = {
    ...payload,
    iat: now,
    exp: now + JWT_EXPIRY_HOURS * 3600,
  };

  const header = base64urlEncode(JSON.stringify({ alg: 'HS256', typ: 'JWT' }));
  const body = base64urlEncode(JSON.stringify(fullPayload));
  const signature = sign(`${header}.${body}`, JWT_SECRET);

  return `${header}.${body}.${signature}`;
}

/**
 * Verify and decode a JWT token.
 */
function verifyToken(token: string): TokenPayload | null {
  try {
    const parts = token.split('.');
    if (parts.length !== 3) return null;

    const [header, body, signature] = parts;

    // Verify signature
    const expectedSig = sign(`${header}.${body}`, JWT_SECRET);
    if (signature !== expectedSig) return null;

    // Decode payload
    const payload: TokenPayload = JSON.parse(base64urlDecode(body));

    // Check expiry
    const now = Math.floor(Date.now() / 1000);
    if (payload.exp < now) return null;

    return payload;
  } catch {
    return null;
  }
}

/**
 * Register auth routes and middleware on the Fastify instance.
 */
export async function registerAuth(app: FastifyInstance) {
  // ─── Login Route ────────────────────────────────────────────────
  app.post('/api/auth/login', async (request: FastifyRequest, reply: FastifyReply) => {
    const { username, password } = request.body as { username?: string; password?: string };

    if (!username || !password) {
      return reply.status(400).send({ error: 'Username and password required' });
    }

    const user = validateCredentials(username, password);
    if (!user) {
      return reply.status(401).send({ error: 'Invalid credentials' });
    }

    const token = createToken({
      username: user.username,
      role: user.role,
      displayName: user.displayName,
    });

    return {
      token,
      user: {
        username: user.username,
        role: user.role,
        displayName: user.displayName,
      },
    };
  });

  // ─── Token verification endpoint ───────────────────────────────
  app.get('/api/auth/me', async (request: FastifyRequest, reply: FastifyReply) => {
    const payload = extractToken(request);
    if (!payload) {
      return reply.status(401).send({ error: 'Not authenticated' });
    }
    return {
      username: payload.username,
      role: payload.role,
      displayName: payload.displayName,
    };
  });
}

/**
 * Extract and verify token from request Authorization header.
 */
export function extractToken(request: FastifyRequest): TokenPayload | null {
  const authHeader = request.headers.authorization;
  if (!authHeader || !authHeader.startsWith('Bearer ')) {
    const query = request.query as { token?: string } | undefined;
    if (!query?.token) return null;
    return verifyToken(query.token);
  }
  const token = authHeader.slice(7);
  return verifyToken(token);
}

/**
 * Middleware factory: requires authentication.
 * Use as a preHandler on routes.
 */
export function requireAuth(request: FastifyRequest, reply: FastifyReply, done: () => void) {
  const payload = extractToken(request);
  if (!payload) {
    reply.status(401).send({ error: 'Authentication required' });
    return;
  }
  // Attach user info to request
  (request as any).user = payload;
  done();
}

/**
 * Middleware factory: requires a minimum role.
 * Usage: { preHandler: requireRole('operator') }
 */
export function requireRole(minRole: UserRole) {
  return (request: FastifyRequest, reply: FastifyReply, done: () => void) => {
    const payload = extractToken(request);
    if (!payload) {
      reply.status(401).send({ error: 'Authentication required' });
      return;
    }
    if (!hasPermission(payload.role, minRole)) {
      reply.status(403).send({ error: `Insufficient permissions. Required: ${minRole}` });
      return;
    }
    (request as any).user = payload;
    done();
  };
}

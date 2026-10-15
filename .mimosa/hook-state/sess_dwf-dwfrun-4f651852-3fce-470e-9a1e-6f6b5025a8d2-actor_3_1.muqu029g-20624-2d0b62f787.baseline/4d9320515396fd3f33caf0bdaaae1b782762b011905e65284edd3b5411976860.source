import { NextResponse } from "next/server";
import { createHash, createHmac, timingSafeEqual } from "node:crypto";

function safeCompare(a: string, b: string): boolean {
  if (!a || !b) return false;
  const hashA = createHash("sha256").update(a).digest();
  const hashB = createHash("sha256").update(b).digest();
  return timingSafeEqual(hashA, hashB);
}

function verifyJwtHs256(token: string, secret: string): boolean {
  const parts = token.split(".");
  if (parts.length !== 3) return false;
  const [headerB64, payloadB64, sigB64] = parts;
  try {
    const dataToSign = `${headerB64}.${payloadB64}`;
    const hmac = createHmac("sha256", secret);
    hmac.update(dataToSign);
    const expectedSig = hmac.digest("base64url");
    if (sigB64.length !== expectedSig.length) return false;
    if (!timingSafeEqual(Buffer.from(sigB64), Buffer.from(expectedSig))) {
      return false;
    }
    const payloadJson = Buffer.from(payloadB64, "base64url").toString("utf-8");
    const payload = JSON.parse(payloadJson) as Record<string, unknown>;
    if (typeof payload.exp === "number") {
      const now = Math.floor(Date.now() / 1000);
      if (now > payload.exp) {
        return false;
      }
    }
    // [P2-05 fix] Role enforcement: a signature-valid JWT without the
    // admin role/subject must not authorize privileged dashboard calls.
    const role = payload.role;
    const sub = payload.sub;
    if (role !== "admin" && sub !== "admin") {
      return false;
    }
    return true;
  } catch {
    return false;
  }
}

/**
 * Extracts and cryptographically validates caller authentication from request Authorization header or cookies.
 * Rejects pseudo-auth or invalid credentials with 401 Unauthorized.
 */
export function extractCallerAuth(request: Request): {
  authenticated: boolean;
  authHeader: string;
  pcToken?: string;
  errorResponse?: NextResponse;
} {
  let authToken = "";
  const authHeader = request.headers.get("authorization") || request.headers.get("Authorization");
  if (authHeader && authHeader.trim()) {
    authToken = authHeader.trim();
  } else {
    const cookieHeader = request.headers.get("cookie");
    if (cookieHeader) {
      const match = cookieHeader.match(/(?:^|;\s*)(?:scp_token|session_token|token)=([^;]+)/);
      if (match && match[1]) {
        authToken = `Bearer ${decodeURIComponent(match[1].trim())}`;
      }
    }
  }

  if (!authToken) {
    return {
      authenticated: false,
      authHeader: "",
      errorResponse: NextResponse.json(
        { error: "Unauthorized: Missing authentication credentials" },
        { status: 401 }
      ),
    };
  }

  const rawToken = authToken.replace(/^Bearer\s+/i, "").trim();
  if (!rawToken) {
    return {
      authenticated: false,
      authHeader: "",
      errorResponse: NextResponse.json(
        { error: "Unauthorized: Empty authentication token" },
        { status: 401 }
      ),
    };
  }

  // Cryptographic token validation:
  // 1. Static admin token / password check (constant time)
  // 2. JWT signature check against configured secrets
  const staticSecrets = [
    process.env.SCP_ADMIN_TOKEN?.trim(),
    process.env.SCP_AUTH_TOKEN_SECRET?.trim(),
    process.env.SCP_ADMIN_KEY?.trim(),
    process.env.SCP_AUTH_PASSWORD?.trim(),
  ].filter((s): s is string => Boolean(s && s.length > 0));

  const jwtSecrets = [
    process.env.SCP_AUTH_TOKEN_SECRET?.trim(),
    process.env.SCP_JWT_SECRET?.trim(),
    process.env.SCP_ADMIN_TOKEN?.trim(),
  ].filter((s): s is string => Boolean(s && s.length > 0));

  // Fail-closed if no secret is configured on server
  if (staticSecrets.length === 0 && jwtSecrets.length === 0) {
    return {
      authenticated: false,
      authHeader: "",
      errorResponse: NextResponse.json(
        { error: "Unauthorized: Authentication secret not configured on server" },
        { status: 401 }
      ),
    };
  }

  let isValid = false;

  // Check constant-time static secret match
  for (const secret of staticSecrets) {
    if (safeCompare(rawToken, secret)) {
      isValid = true;
      break;
    }
  }

  // Check JWT signature if token has JWT structure
  if (!isValid && rawToken.split(".").length === 3) {
    for (const secret of jwtSecrets) {
      if (verifyJwtHs256(rawToken, secret)) {
        isValid = true;
        break;
      }
    }
  }

  if (!isValid) {
    return {
      authenticated: false,
      authHeader: "",
      errorResponse: NextResponse.json(
        { error: "Unauthorized: Invalid or expired credentials" },
        { status: 401 }
      ),
    };
  }

  const authHeaderToSend = authToken.toLowerCase().startsWith("bearer ")
    ? authToken
    : `Bearer ${authToken}`;

  const pcToken = request.headers.get("x-scp-pc-token") || request.headers.get("X-SCP-PC-Token") || undefined;

  return {
    authenticated: true,
    authHeader: authHeaderToSend,
    pcToken,
  };
}

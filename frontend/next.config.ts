import type { NextConfig } from "next";

// --- Content-Security-Policy Generation ---
// Implements least-privilege CSP source construction:
// 1. In production with no NEXT_PUBLIC_API_BASE_URL: connect-src 'self' without localhost, ws:, or wss:.
// 2. In production with a valid API URL: connect-src 'self' <origin> using parsed URL origin only; requires https: protocol.
// 3. In development: accepts http: or https: API URLs; uses explicit HMR WebSocket origins (no broad ws: or wss:).
// 4. Rejects malformed API URL configuration or non-HTTPS production URLs with a clear error.
// 5. img-src adheres to least privilege: 'self' data: blob: (and parsed API origin if configured).
// 6. unsafe-eval is strictly absent. unsafe-inline in script-src is retained for Next.js bootstrapping.
//
// HSTS: Not set here because Next.js serves over HTTP in development and
// the production HSTS header must be set at the reverse proxy / CDN layer
// (e.g. Vercel's edge, Nginx, Cloudflare) to cover all redirects.
// Do NOT emit Strict-Transport-Security from Next.js because it would be sent
// over plain HTTP responses too before TLS termination.

export interface CspEnv {
  NODE_ENV?: string;
  NEXT_PUBLIC_API_BASE_URL?: string;
}

export function buildCsp(env: CspEnv = process.env): string {
  const isDev = env.NODE_ENV === "development";
  const rawApiUrl = env.NEXT_PUBLIC_API_BASE_URL?.trim();

  let validatedApiOrigin = "";

  if (rawApiUrl) {
    let parsed: URL;
    try {
      parsed = new URL(rawApiUrl);
    } catch (err: any) {
      throw new Error(
        `Invalid NEXT_PUBLIC_API_BASE_URL '${rawApiUrl}': malformed URL. ` +
        `Must be an absolute URL like 'https://api.example.com'.`
      );
    }
    if (isDev) {
      if (parsed.protocol !== "http:" && parsed.protocol !== "https:") {
        throw new Error(
          `Invalid protocol '${parsed.protocol}' in NEXT_PUBLIC_API_BASE_URL '${rawApiUrl}'. ` +
          `Development API URL must use 'http:' or 'https:'.`
        );
      }
    } else {
      if (parsed.protocol !== "https:") {
        throw new Error(
          `Invalid protocol '${parsed.protocol}' in NEXT_PUBLIC_API_BASE_URL '${rawApiUrl}'. ` +
          `Production API URL must use 'https:' protocol.`
        );
      }
    }
    // Explicit origin only (scheme + host + port), without trailing slash or path
    validatedApiOrigin = parsed.origin;
  }

  let connectSources: string[];
  let imgSources: string[];

  if (isDev) {
    // Development mode: permit local dev API server and explicit HMR WebSockets.
    // Broad 'ws:' and 'wss:' wildcards are strictly removed.
    connectSources = [
      "'self'",
      "http://localhost:8000",
      "http://127.0.0.1:8000",
      "ws://localhost:3000",
      "ws://127.0.0.1:3000",
      "wss://localhost:3000",
      "wss://127.0.0.1:3000",
    ];
    if (validatedApiOrigin && !connectSources.includes(validatedApiOrigin)) {
      connectSources.push(validatedApiOrigin);
    }
    imgSources = [
      "'self'",
      "data:",
      "blob:",
      "http://localhost:8000",
      "http://127.0.0.1:8000",
    ];
    if (validatedApiOrigin && !imgSources.includes(validatedApiOrigin)) {
      imgSources.push(validatedApiOrigin);
    }
  } else {
    // Production mode: least-privilege sources only.
    // Never include localhost, 127.0.0.1, broad 'ws:', 'wss:', or wildcard 'https:'.
    if (validatedApiOrigin) {
      connectSources = ["'self'", validatedApiOrigin];
      imgSources = ["'self'", "data:", "blob:", validatedApiOrigin];
    } else {
      connectSources = ["'self'"];
      imgSources = ["'self'", "data:", "blob:"];
    }
  }

  const cspDirectives = [
    "default-src 'self'",
    "script-src 'self' 'unsafe-inline'",
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
    "font-src 'self' https://fonts.gstatic.com data:",
    `img-src ${imgSources.join(" ")}`,
    `connect-src ${connectSources.join(" ")}`,
    "frame-ancestors 'none'",
    "base-uri 'self'",
    "form-action 'self'",
  ];

  return cspDirectives.join("; ").replace(/\s{2,}/g, " ").trim();
}

const nextConfig: NextConfig = {
  images: {
    unoptimized: true,
  },
  async headers() {
    return [
      {
        source: "/:path*",
        headers: [
          {
            key: "Content-Security-Policy",
            value: buildCsp(),
          },
          {
            key: "X-Content-Type-Options",
            value: "nosniff",
          },
          {
            key: "X-Frame-Options",
            value: "DENY",
          },
          {
            key: "Referrer-Policy",
            value: "strict-origin-when-cross-origin",
          },
          {
            key: "Permissions-Policy",
            value: "camera=(), microphone=(), geolocation=(), interest-cohort=()",
          },
        ],
      },
    ];
  },
};

export default nextConfig;

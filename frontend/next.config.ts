import type { NextConfig } from "next";

// --- Content-Security-Policy ---
// NOTES ON REMAINING DIRECTIVES:
//
// script-src 'unsafe-inline':
//   Next.js 14/15/16 injects small inline scripts (chunk bootstrapping, __NEXT_DATA__).
//   Removing 'unsafe-inline' requires a nonce strategy threaded through
//   Next.js middleware and custom App/Document — not done here. The risk is
//   accepted for anonymous-session demo use. A future hardening pass should
//   implement a per-request nonce via Next.js middleware and headers().
//
// 'unsafe-eval' is REMOVED. It is only required in Next.js dev mode (webpack
//   hot-reload). Production builds do not use eval(). Removing it means any
//   eval-based injection attempt would be blocked in production.
//
// connect-src: explicitly enumerates the API base URL from the environment
//   variable (same origin in production split-hosting, localhost in dev).
//   Falls back to 'self' only if no API URL is configured (pure demo mode).
//
// HSTS: Not set here because Next.js serves over HTTP in development and
//   the production HSTS header must be set at the reverse proxy / CDN layer
//   (e.g. Vercel's edge, Nginx, Cloudflare) to cover all redirects.
//   Vercel automatically sends HSTS (max-age=63072000; includeSubDomains;
//   preload) for custom domains on Pro/Team plans; verify in Vercel dashboard
//   under Domains → HSTS. Do NOT emit Strict-Transport-Security from Next.js
//   because it would be sent over HTTP responses too (before HTTPS redirect).

const API_ORIGIN =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/+$/, "") ||
  (process.env.NODE_ENV === "development"
    ? "http://localhost:8000 http://127.0.0.1:8000"
    : "");

const connectSrc = API_ORIGIN ? `'self' ${API_ORIGIN} ws: wss:` : "'self' ws: wss:";

const cspHeader = [
  "default-src 'self'",
  "script-src 'self' 'unsafe-inline'",
  "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
  "font-src 'self' https://fonts.gstatic.com data:",
  `img-src 'self' data: blob: ${API_ORIGIN || "http://localhost:8000 http://127.0.0.1:8000"} https:`,
  `connect-src ${connectSrc}`,
  "frame-ancestors 'none'",
  "base-uri 'self'",
  "form-action 'self'",
]
  .join("; ")
  .replace(/\s{2,}/g, " ")
  .trim();

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
            value: cspHeader,
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

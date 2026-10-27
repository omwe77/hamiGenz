import assert from "node:assert/strict";
import { buildCsp } from "../next.config.ts";

function getDirective(csp: string, directiveName: string): string {
  const parts = csp.split(";").map((p) => p.trim());
  const match = parts.find((p) => p.startsWith(`${directiveName} `));
  if (!match) {
    throw new Error(`Directive '${directiveName}' not found in CSP: ${csp}`);
  }
  return match.slice(directiveName.length).trim();
}

console.log("Starting CSP configuration automated test suite...");

// ─── 1. Production with NO API URL ──────────────────────────────────────────
{
  const csp = buildCsp({ NODE_ENV: "production", NEXT_PUBLIC_API_BASE_URL: "" });
  const connectSrc = getDirective(csp, "connect-src");
  const imgSrc = getDirective(csp, "img-src");
  const scriptSrc = getDirective(csp, "script-src");

  // In production with no API URL: strictly 'self'
  assert.strictEqual(connectSrc, "'self'", "connect-src must be exactly 'self' in production with no API URL");

  // Must not contain localhost or loopback
  assert(!connectSrc.includes("localhost"), "connect-src must not contain localhost in production");
  assert(!connectSrc.includes("127.0.0.1"), "connect-src must not contain 127.0.0.1 in production");
  assert(!connectSrc.includes("8000"), "connect-src must not contain port 8000 in production");

  // Must not contain wildcard or bare ws: / wss: schemes
  assert(!connectSrc.includes("ws:"), "connect-src must not contain ws: scheme in production");
  assert(!connectSrc.includes("wss:"), "connect-src must not contain wss: scheme in production");

  // img-src must adhere to least privilege: 'self' data: blob:
  assert.strictEqual(imgSrc, "'self' data: blob:", "img-src must be exactly 'self' data: blob: in production");
  assert(!imgSrc.includes("localhost"), "img-src must not contain localhost in production");
  assert(!imgSrc.includes("https:"), "img-src must not contain broad https: in production");

  // script-src must not contain unsafe-eval
  assert(!scriptSrc.includes("'unsafe-eval'"), "script-src must never contain 'unsafe-eval'");
  console.log("✓ Production with no API URL passes least-privilege checks");
}

// ─── 2. Production with Valid API URL ───────────────────────────────────────
{
  const validUrl = "https://api.hamigenz.gov.np/api/v1/documents?param=1";
  const csp = buildCsp({
    NODE_ENV: "production",
    NEXT_PUBLIC_API_BASE_URL: validUrl,
  });
  const connectSrc = getDirective(csp, "connect-src");
  const imgSrc = getDirective(csp, "img-src");

  // Must only allow 'self' and parsed origin (protocol + host + optional port), no path or query
  assert.strictEqual(
    connectSrc,
    "'self' https://api.hamigenz.gov.np",
    "connect-src must contain 'self' and parsed origin only"
  );
  assert.strictEqual(
    imgSrc,
    "'self' data: blob: https://api.hamigenz.gov.np",
    "img-src must contain 'self', data:, blob:, and parsed origin only"
  );

  // Must not contain localhost or bare ws:/wss:
  assert(!connectSrc.includes("localhost"));
  assert(!connectSrc.includes("ws:"));
  assert(!connectSrc.includes("wss:"));
  console.log("✓ Production with valid API URL permits only parsed origin");
}

// ─── 3. Production with Malformed API URL ───────────────────────────────────
{
  const malformedUrls = [
    "not-a-valid-url",
    "://missing-scheme",
    "ftp://unsupported-protocol.com",
    "javascript:alert(1)",
    "data:text/html,<html>",
  ];

  for (const badUrl of malformedUrls) {
    assert.throws(
      () => {
        buildCsp({
          NODE_ENV: "production",
          NEXT_PUBLIC_API_BASE_URL: badUrl,
        });
      },
      (err: any) => {
        return err instanceof Error && err.message.includes("Invalid");
      },
      `Should throw clear configuration error for malformed API URL: ${badUrl}`
    );
  }
  console.log("✓ Production with malformed API URL fails closed with descriptive error");
}

// ─── 4. Development Mode ────────────────────────────────────────────────────
{
  const csp = buildCsp({ NODE_ENV: "development", NEXT_PUBLIC_API_BASE_URL: "" });
  const connectSrc = getDirective(csp, "connect-src");
  const imgSrc = getDirective(csp, "img-src");

  // Development mode must permit local backend and HMR
  assert(connectSrc.includes("'self'"), "Dev connect-src must include 'self'");
  assert(connectSrc.includes("http://localhost:8000"), "Dev connect-src must include localhost:8000");
  assert(connectSrc.includes("http://127.0.0.1:8000"), "Dev connect-src must include 127.0.0.1:8000");
  assert(connectSrc.includes("ws:"), "Dev connect-src must include ws: for HMR");

  assert(imgSrc.includes("http://localhost:8000"), "Dev img-src must include localhost:8000");
  assert(imgSrc.includes("http://127.0.0.1:8000"), "Dev img-src must include 127.0.0.1:8000");
  console.log("✓ Development mode permits necessary local dev origins and HMR WebSockets");
}

console.log("=======================================================");
console.log("ALL CSP AUTOMATED TEST CHECKS PASSED SUCCESSFULLY!");
console.log("=======================================================");


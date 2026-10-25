# hamiGenZ Frontend

The web client for **hamiGenZ** — Nepal's evidence-grounded AI civic document understanding platform. Built with **Next.js 16 (App Router)**, **React 19**, and **TypeScript**.

---

## Overview

The hamiGenZ frontend provides a civic document workspace designed for accessibility, transparency, and auditability:
- **Landing Page**: Features a scroll-driven, continuous SVG provenance thread animation, interactive document sandbox preview, and responsive capability breakdowns.
- **Interactive Workspace**: A split-screen environment with document reading, dual-script previews (Devanagari / English), inline citation attribution, in-document keyword search, civic checklist extraction, and reference-filled form previewing.
- **Offline Demo Mode**: Embedded offline client architecture that allows full interactive exploration on public cloud deployments (such as Vercel) without requiring an active backend or local GPU instance.

---

## Architecture & Component Structure

```text
frontend/
├── src/
│   ├── app/
│   │   ├── layout.tsx                # Global layout, fonts, and metadata
│   │   ├── page.tsx                  # Landing page with full-page ProvenanceThread
│   │   ├── globals.css               # Design tokens, responsive utilities, and motion keyframes
│   │   └── workspace/
│   │       ├── page.tsx              # Main workspace route
│   │       └── [docId]/page.tsx      # Deep linkable document view route (SSG)
│   ├── components/
│   │   ├── motion/
│   │   │   ├── ProvenanceThread.tsx  # Continuous full-page scroll-drawn SVG spline
│   │   │   ├── AnimatedDocumentSandbox.tsx # Interactive document viewer preview
│   │   │   ├── CapabilitiesSection.tsx     # Three-stage pipeline (Read / Understand / Verify)
│   │   │   └── HeroTypography.tsx    # Accessible hero headlines and badge
│   │   └── workspace/
│   │       ├── WorkspacePage.tsx     # Primary stateful workspace container
│   │       ├── DocumentViewer.tsx    # PDF / image page canvas with search match navigation
│   │       ├── ExplanationPanel.tsx  # Multi-level explanations (Simple / Plain / Bullet)
│   │       ├── CitationChip.tsx      # Clickable, traceable citation chips
│   │       ├── FormPanel.tsx         # Detected civic form fields and requirements
│   │       └── FillPanel.tsx         # Reference form fill helper and canvas preview
│   └── lib/
│       ├── hamigenz-api.ts           # Unified API client & offline sample fallback provider
│       ├── motion.ts                 # Animation utilities and prefers-reduced-motion checks
│       └── types.ts                  # Shared TypeScript data models
└── test/
    └── demo-mode.test.ts             # 12-stage offline test suite
```

---

## Prerequisites

- **Node.js**: `20.9.0` or higher (required by Next.js 16)
- **Package Manager**: `npm` (v10+ recommended)

---

## Environment Configuration

Copy the template to create your local environment file:

```bash
cp .env.example .env.local
```

| Variable | Default | Purpose |
|---|---|---|
| `NEXT_PUBLIC_API_BASE_URL` | `http://127.0.0.1:8000` | URL of the running FastAPI backend. If left unset or unreachable on a remote deployment, the frontend automatically activates **Offline Demo Mode**. |

---

## Development & Build Commands

All commands are run from the `frontend/` directory:

```bash
# Install dependencies
npm install

# Start development server with Turbopack (http://localhost:3000)
npm run dev

# Run automated Demo Mode test suite (12 checks, zero network calls)
npm run test

# Type-check TypeScript without emitting JS
npx tsc --noEmit

# Lint code with Next.js ESLint configuration
npm run lint

# Build production bundle with static optimization
npm run build

# Start local production server on port 3000
npm run start
```

---

## Demo Mode vs. Live Backend Mode

1. **Public Demo Mode (Default on Vercel):**
   - Operates entirely client-side using illustrative fixtures (e.g., `registration_form_sample.pdf`).
   - Does not attempt network calls to `127.0.0.1` or third-party cloud APIs on public hostnames.
   - Any uploaded user documents in Demo Mode are retained strictly within transient browser state and are not uploaded to a backend server.
   - **Notice:** Sample notices, fees, and deadlines are for interface demonstration only and must not be relied upon for real civic or administrative applications.
2. **Live Backend Mode:**
   - Activated automatically when `NEXT_PUBLIC_API_BASE_URL` points to an active FastAPI backend with Ollama (`qwen3:8b`).
   - Supports live Devanagari OCR, dynamic FAISS vector embedding generation, and real-time LLM inference.
   - If connection to the backend fails, the workspace surfaces a clear, recoverable error notice with a one-click return to Demo Mode.

---

## Related Documentation

- [Root Repository README](../README.md): Full-stack overview, backend setup, OKF architecture, and evaluation results.
- [Deployment Guide](../docs/DEPLOYMENT.md): Production Vercel deployment details and self-hosted backend requirements.
- [Evaluation Report](../docs/EVALUATION.md): Retrieval benchmarks and explanation quality metrics.

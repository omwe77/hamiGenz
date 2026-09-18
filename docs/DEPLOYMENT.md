# hamiGenZ — Staging Deployment Guide

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│              Azure Static Web Apps (Free)                │
│           Frontend: https://hamigenz-staging.<region>    │
│            GitHub Actions CI/CD on push to main         │
└────────────────────────┬────────────────────────────────┘
                         │ NEXT_PUBLIC_API_BASE_URL
                         ▼
┌─────────────────────────────────────────────────────────┐
│           Azure Linux VM — Standard_B2ms_v2              │
│        2 vCPU / 8 GiB RAM / East US                     │
│                                                          │
│  ┌──────────────┐    ┌──────────────┐    ┌───────────┐  │
│  │  Nginx (443) │───▶│ FastAPI     │───▶│ Ollama    │  │
│  │  HTTPS +     │    │ + Uvicorn   │    │ qwen3:8b  │  │
│  │  CORS +      │    │ port 8000   │    │ port 11434│  │
│  │  rate limit   │    │             │    │ (local)   │  │
│  └──────────────┘    └──────────────┘    └───────────┘  │
│                                                          │
│  ┌──────────────────────────────────────────────────┐   │
│  │ Tesseract + nep/eng/osd traineddata              │   │
│  │ sentence-transformers multilingual-MiniLM-L12    │   │
│  │ data/uploads/  data/vectors/  hamigenz.db        │   │
│  │ systemd: ollama.service + hamiapi.service        │   │
│  └──────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

## Azure Resources

| Resource | Name | SKU | Est. Monthly |
|---|---|---|---|
| Static Web App | `hamigenz-staging` | Free | $0 |
| Virtual Machine | `hamigenz-staging-vm` | Standard_B2ms_v2 | ~$46 |
| Managed Disk | `hamigenz-staging-disk` | P10 (64 GiB SSD) | ~$8 |
| Public IP | attached to VM | — | ~$0.80 |

**Total: ~$55/month.** With $80 credit → ~1.5 months. Budget alert at 60%.

## Why B2ms_v2

- `qwen3:8b` Q4_K_M needs ~4.5 GiB; Ollama + Python + embeddings + OS → 8 GiB safe minimum.
- B1s (1 GiB), B1ls (0.5 GiB), B2s (4 GiB) all too small — would OOM or swap badly.
- B2ms_v2 is the cheapest VM that runs the model reliably.

## Deployment Flow

```
git push to main
    │
    ├──────────────────────────────┐
    ▼                              ▼
Frontend GH Action           Backend GH Action
(azure/static-web-apps-deploy)  (SSH to VM)
    │                              │
    ▼                              ▼
Azure SWA builds + deploys   git pull + restart
    │                              │
    ▼                              ▼
https://hamigenz-staging.<region>  https://<vm-public-ip>
         │                              │
         └────────── API calls ─────────┘
```

## Frontend CI/CD

File: `.github/workflows/deploy-frontend.yml`

- Triggers on push to `main`
- Builds Next.js with `output: "export"` → `frontend/out/`
- Deploys to Azure Static Web Apps via `azure/static-web-apps-deploy@v1`
- Sets `NEXT_PUBLIC_API_BASE_URL` to the backend VM URL

## Backend CI/CD

File: `.github/workflows/deploy-backend.yml`

- Triggers on push to `main`
- SSH into VM, `cd /opt/hamigenz`, `git pull`, `sudo systemctl restart hamiapi`
- Ollama model already on disk — no re-pull needed unless model changed

## VM Setup (one-time, manual)

See `docs/VM_SETUP.md` for the full provisioning script.

Summary:
1. Create Ubuntu 24.04 VM, Standard_B2ms_v2, East US
2. Open NSG: 443 from 0.0.0.0/0, 22 from your IP only
3. SSH in, install: nginx, python3.12, ollama, tesseract + traineddata, system deps
4. Copy `backend/` + `data/` (test data only) to `/opt/hamigenz/`
5. `ollama pull qwen3:8b`
6. Set env vars in `/etc/hamigenz/env`
7. Create systemd units: `ollama.service`, `hamiapi.service`
8. Configure nginx reverse proxy with Let's Encrypt or self-signed for staging

## Environment Variables

| Variable | Dev | Staging |
|---|---|---|
| `NEXT_PUBLIC_API_BASE_URL` | `http://127.0.0.1:8000` | `https://<vm-hostname>` |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | `http://localhost:11434` |
| `OLLAMA_MODEL` | `qwen3:8b` | `qwen3:8b` |
| `FRONTEND_ORIGIN` | `http://localhost:3000` | `https://hamigenz-staging.<region>` |
| `REINDEX_ON_STARTUP` | `1` | `1` |

Set backend env vars via systemd `EnvironmentFile=/etc/hamigenz/env`. Set frontend via GitHub Actions workflow env.

## Document Storage

- `data/uploads/`, `data/vectors/`, `hamigenz.db` live on VM disk only.
- Never committed to Git (in `.gitignore`).
- Staging test data: `data/passport_procedure.pdf` + synthetic forms only. No private documents.

## Security (Staging Minimum)

- Nginx terminates HTTPS (self-signed cert acceptable for staging; real cert if custom domain set up).
- Ollama port 11434 NOT exposed to public — only localhost.
- NSG blocks all ports except 443 and 22 (source-restricted).
- CORS allowlist: only the SWA frontend origin.
- No `.env`, credentials, or secrets in Git.
- FastAPI runs with `debug=False` (default in production).
- Upload limits: 50 MB, magic-byte validation, UUID filenames, path containment.
- Rate limiting on /upload, /ask, /explain, /ask-general, /search-text.

## Health Check

`GET https://<vm-hostname>/health` returns:

```json
{
  "status": "ok",
  "service": "hamigenz",
  "version": "0.1.0",
  "ollama_model": "qwen3:8b",
  "embedder": "paraphrase-multilingual-MiniLM-L12-v2"
}
```

Distinguishes: backend alive, Ollama unavailable (warning logged, 503 on LLM calls), model unavailable (same), retrieval failure (empty answer, not crash).

## Staging Test Data

Safe public test set:
- `data/passport_procedure.pdf` — public Nepal passport procedure document (6 pages)
- `data/knowledge/passport-dept.json` — passport department knowledge entry
- `data/knowledge/dotm.json` — Department of Transportation knowledge entry
- `data/knowledge/nrc.json` — National Register Certificate knowledge entry
- Synthetic Nepali forms (generated, no real identity data)
- Synthetic difficult-Nepali examples (OCR test images in `tests/`)
- English examples
- Romanized Nepali examples

## Performance Targets (to measure on staging)

| Metric | Target | How to measure |
|---|---|---|
| Initial page load | < 3s | browser DevTools Network |
| API latency (no LLM) | < 200ms | curl /health, /documents |
| Model response time | < 15s | /ask with simple query |
| OCR time (1 page) | < 5s | upload scanned PNG |
| Document processing (6 pages) | < 30s | upload passport PDF |
| Memory usage (idle) | < 4 GiB | `htop` on VM |
| Memory usage (model loaded) | < 7 GiB | `htop` on VM after first query |
| Startup time (full) | < 60s | time from VM boot to /health 200 |
| Model load time | < 120s | time from ollama serve start to first successful generate |

## Cost Control

1. Azure budget alert: set at 60% of $80 credit (~$48) via Azure Cost Management.
2. Tag all resources with `project=hamigenz`, `environment=staging`.
3. If credit runs low: stop VM (not delete) to preserve disk; restart when needed.
4. Delete everything: `az group delete --name hamigenz-staging-rg --yes`.

## Remaining Limitations

- No custom domain yet (SWA free tier supports it, but DNS not configured).
- Staging uses self-signed TLS unless we set up Let's Encrypt on the VM.
- No authentication — anyone with the URL can upload and query.
- Single VM is a single point of failure; VM reboot = downtime until systemd restarts services.
- qwen3:8b inference is CPU-bound on this VM; expect several seconds per response.
- No persistent external storage — rebooting the VM loses nothing (disk is persistent), but deleting the VM deletes all uploaded documents and vectors.

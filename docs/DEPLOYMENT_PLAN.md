# hamiGenZ — Azure Staging Deployment Plan

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│              Azure Static Web Apps (Free)                │
│           Frontend: https://hamigenz-staging             │
│            GitHub Actions CI/CD on push to main         │
└────────────────────────┬────────────────────────────────┘
                         │ NEXT_PUBLIC_API_BASE_URL
                         ▼
┌─────────────────────────────────────────────────────────┐
│           Azure Linux VM — Standard_B2ms_v2              │
│        2 vCPU / 8 GiB RAM / ~€46/mo (East US)           │
│                                                          │
│  ┌──────────────┐    ┌──────────────┐    ┌───────────┐  │
│  │  Nginx (443) │───▶│ FastAPI     │───▶│ Ollama    │  │
│  │  HTTPS +     │    │ + Uvicorn   │    │ qwen3:8b  │  │
│  │  CORS +      │    │ port 8000   │    │ port 11434│  │
│  │  rate limit   │    │             │    │ (local)   │  │
│  └──────────────┘    └──────────────┘    └───────────┘  │
│                                                          │
│  ┌──────────────────────────────────────────────────┐   │
│  │ Tesseract (system) + nep/eng/osd traineddata     │   │
│  │ sentence-transformers (multilingual-MiniLM-L12)  │   │
│  │ data/uploads/  data/vectors/  hamigenz.db        │   │
│  │ systemd: ollama.service + hamiapi.service        │   │
│  └──────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

## Selected SKUs

| Component | Azure Service | Tier | Est. Cost |
|---|---|---|---|
| Frontend | Static Web Apps | Free | $0 |
| Backend | VM | Standard_B2ms_v2 | ~$46/mo |
| Disk | Managed disk (64 GiB SSD) | P10 | ~$8/mo |
| Networking | Public IP + NSG | — | ~$0.80/mo |
| **Total** | | | **~$55/mo** |

Cost basis: ~$80 credit → ~1.5 months staging. Budget alert at 60%.

## VM Rationale

- `qwen3:8b` at Q4_K_M needs ~4.5 GiB; plus Ollama, Python, embeddings, OS → 8 GiB is the smallest safe choice.
- `Standard_B1s_v2` (1 vCPU/1 GiB) and `B1ls` (0.5 GiB) cannot load the model.
- `B2s` (4 GiB) is too tight; swapping would degrade responses unacceptably.
- `B2ms_v2` (8 GiB) is the cheapest VM that runs the model without constant OOM.

## Networking

- NSG: allow 443 from 0.0.0.0/0; allow 22 only from laptop IP.
- Ollama port 11434 NOT exposed — backend talks to it on localhost.
- No public IP on data/vectors/uploads — only via FastAPI.

## CI/CD

- Frontend: GitHub Actions → Azure SWA on every push to `main`. `.github/workflows/deploy-frontend.yml`.
- Backend: GitHub Actions SSH-deploy to VM on push to `main`. `.github/workflows/deploy-backend.yml`.
- Both use the same trigger; frontend deploys first, backend second.

## Environment Variables

| Variable | Dev | Staging |
|---|---|---|
| `NEXT_PUBLIC_API_BASE_URL` | `http://127.0.0.1:8000` | `https://hamigenz-api.<region>.azure...` |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | `http://localhost:11434` |
| `OLLAMA_MODEL` | `qwen3:8b` | `qwen3:8b` |
| `FRONTEND_ORIGIN` | `http://localhost:3000` | `https://hamigenz-staging...` |
| `REINDEX_ON_STARTUP` | `1` | `1` |

No secrets in Git. VM env vars set via systemd `EnvironmentFile`.

## Document Storage (Staging)

- `data/uploads/` on VM disk only. Never committed.
- Test with `data/passport_procedure.pdf` + synthetic forms only.
- No private documents on staging.

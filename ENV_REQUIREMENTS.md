# Environment Requirements — KrishiVoice / SIH-MVP

Copy this into `krishivoice/backend/.env` after clone. **Do not commit `.env`.**

Template file: `krishivoice/backend/.env.example`

---

## Required setup

| Step | Command |
|------|---------|
| Python deps | `cd krishivoice/backend && pip install -r requirements.txt` |
| Frontend deps | `cd krishivoice/frontend && npm install` |
| Create env file | `cp krishivoice/backend/.env.example krishivoice/backend/.env` |

---

## Environment variables

### Core (defaults work for local demo)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `CORS_ORIGINS` | No | `http://localhost:5173,...` | Allowed frontend origins |
| `DATABASE_URL` | No | PostgreSQL local URL | Only if using Postgres |
| `DATA_DIR` | No | `../data/processed` | Processed indexes path |
| `USE_OPENMETEO` | No | `true` | Live weather via Open-Meteo (no API key) |

### OpenRouter — optional (VL soil OCR + LLM polish)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OPENROUTER_API_KEY` | Optional | — | Get from [openrouter.ai](https://openrouter.ai) |
| `OPENROUTER_ENABLED` | No | `true` | Set `false` to disable |
| `OPENROUTER_VL_MODEL` | No | `nvidia/nemotron-nano-12b-v2-vl:free` | Vision model |
| `OPENROUTER_LLM_MODEL` | No | `nvidia/nemotron-3-nano-30b-a3b:free` | Text model |

### Tavily — optional (web search when globe icon is ON)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `TAVILY_API_KEY` | Optional | — | Get from [tavily.com](https://tavily.com) |
| `TAVILY_ENABLED` | No | `true` | Set `false` to disable |
| `TAVILY_TRUSTED_ONLY` | No | `true` | Restrict to trusted sources |

### data.gov.in — optional (AGMARKNET live mandi prices)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATA_GOV_IN_API_KEY` | Optional | demo key (rate-limited) | Free at [data.gov.in](https://data.gov.in) → My Account → API Key |
| `MANDI_DEFAULT_STATE` | No | `Tamil Nadu` | State filter for mandi API |
| `MANDI_CACHE_SECONDS` | No | `21600` | Cache TTL (6 hours) |

---

## Minimal `.env` example

```env
CORS_ORIGINS=http://localhost:5173,http://localhost:5174,http://localhost:3000

# Optional — add keys only if you use these features
OPENROUTER_API_KEY=
OPENROUTER_ENABLED=true
TAVILY_API_KEY=
TAVILY_ENABLED=true
DATA_GOV_IN_API_KEY=
MANDI_DEFAULT_STATE=Tamil Nadu
```

---

## Run commands

```powershell
# Backend (port 8010)
cd krishivoice/backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8010 --reload

# Frontend (port 5173)
cd krishivoice/frontend
npm run dev
```

Demo login: `demo` / `demo1234`

---

## Notes

- **Open-Meteo** needs no key (weather/climate queries work out of the box).
- **AGMARKNET** may timeout on slow networks; app falls back gracefully.
- Never push real API keys to GitHub — use `.env` locally only.

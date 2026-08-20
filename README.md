# SIH-MVP — KrishiVoice

Tamil Nadu farmer advisory platform: voice/chat in Tamil & Tanglish, crop advice, live weather, AGMARKNET mandi prices, and multi-dataset RAG.

## Repository layout

| Path | Description |
|------|-------------|
| `krishivoice/` | Main app (FastAPI backend + React frontend) |
| `*.csv` | Training / RAG datasets (root level) |
| `ENV_REQUIREMENTS.md` | **Environment variables & setup (read this first)** |
| `krishivoice/backend/.env.example` | Env template to copy → `.env` |

## Quick start

1. Read **[ENV_REQUIREMENTS.md](./ENV_REQUIREMENTS.md)** and create `krishivoice/backend/.env`
2. Install backend: `pip install -r krishivoice/backend/requirements.txt`
3. Install frontend: `cd krishivoice/frontend && npm install`
4. Run backend: `python -m uvicorn app.main:app --host 127.0.0.1 --port 8010 --reload` (from `krishivoice/backend`)
5. Run frontend: `npm run dev` (from `krishivoice/frontend`)
6. Open http://localhost:5173

## Demo

- Guest mode or login: `demo` / `demo1234`
- Try: weather, market rates (sidebar), crop questions in Tamil/Tanglish

## Large datasets

Soil locality files (~148 MB) are **gitignored** (GitHub 100 MB limit). Place them locally under `krishivoice/data/processed/` if needed for soil ML features.

> Demo farm data is **synthetic** — not official government records.

# KrishiVoice

Field-specific agricultural intelligence and voice advisory platform for Tamil Nadu farmers (MVP: Thanjavur & Cuddalore).

> **Demo data is SYNTHETIC** — not official government records.

## Quick Start

```bash
# 1. Generate synthetic demo dataset
cd data/scripts
pip install -r requirements.txt
python generate_synthetic_data.py

# 2. Validate & preprocess
python validate_data.py

# 3. Start PostgreSQL (Docker)
cd ../..
docker compose up -d postgres

# 4. Backend
cd backend
pip install -r requirements.txt
cp .env.example .env
python -m app.db.seed

# 5. Run API
uvicorn app.main:app --reload --port 8000

# 6. Frontend
cd ../frontend
npm install
npm run dev
```

## Demo Scenario

- **Farmer:** F0042
- **Parcel:** P0187
- **Region:** Thanjavur
- **Crop:** Rice (Tillering)
- **Question:** "இன்னைக்கு தண்ணீர் பாய்ச்சணுமா?"

## Architecture

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)

## Team Roles

| Member | Focus |
|--------|-------|
| 1 | Data pipeline, PostgreSQL, validation |
| 2 | FastAPI, auth, advisory service |
| 3 | ML models (yield, irrigation, risk) |
| 4 | React dashboard |
| 5 | Voice AI (STT, intent, TTS Tamil) |

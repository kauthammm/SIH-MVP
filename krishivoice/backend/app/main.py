from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routes.api import router

settings = get_settings()

app = FastAPI(
    title="KrishiVoice API",
    description="Field-specific agricultural intelligence for Tamil Nadu farmers",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api/v1")


@app.on_event("startup")
def preload_convo_index():
    """Warm up convodataset vector index so first voice query is fast."""
    try:
        from app.services.user_auth import ensure_demo_user
        ensure_demo_user()
    except Exception as e:
        print(f"User auth init skipped: {e}")
    try:
        from app.services.convo_dataset_rag import index_stats
        stats = index_stats()
        if stats.get("loaded"):
            print(f"Convo dataset index loaded: {stats.get('rows', 0):,} Q&A pairs")
    except Exception as e:
        print(f"Convo index preload skipped: {e}")


@app.get("/")
def root():
    return {
        "name": "KrishiVoice",
        "docs": "/docs",
        "demo_farmer": "F0042",
        "demo_parcel": "P0187",
    }

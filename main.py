# main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.config import settings
from routers import transactions, webhooks, escrow, auth

app = FastAPI(
    title="tap. Robust Infrastructure API",
    description="One-tap payment and escrow engine for African social commerce.",
    version="1.0.0",
)

# ── CORS Configuration ───────────────────────────────────────────
# This allows your Next.js frontend to securely talk to this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.BASE_URL, 
        "http://localhost:3000", # Local Next.js dev server
        "https://usetap.vercel.app" # Your live waitlist/frontend
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Router Registration ──────────────────────────────────────────
# This attaches your "Front Doors" to the main application
app.include_router(auth.router, prefix="/api/v1")
app.include_router(transactions.router, prefix="/api/v1")
app.include_router(webhooks.router, prefix="/api/v1")
app.include_router(escrow.router, prefix="/api/v1")

# ── Health Check ─────────────────────────────────────────────────
@app.get("/")
async def root():
    """Simple endpoint to verify the server is running."""
    return {
        "status": "operational", 
        "service": "tap. escrow-engine v1",
        "environment": settings.ENVIRONMENT
    }
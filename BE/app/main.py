import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

logging.basicConfig(level=logging.INFO)

from app.core.config import settings
from app.core.db import engine
from app.api.routes import auth, youtube, competitor, subtitle, persona, recommendations, script_gen, thumbnail
from app.api.routes.channel import router as channel_router

# Create FastAPI app
app = FastAPI(
    title="YouTube Maker API",
    description="Backend API for YouTube content creation platform",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(youtube.router)
app.include_router(competitor.router)
app.include_router(subtitle.router)
app.include_router(persona.router)
app.include_router(recommendations.router)
app.include_router(script_gen.router)
app.include_router(thumbnail.router)
app.include_router(channel_router)

# Static files: 생성된 썸네일 이미지 서빙
thumbnails_dir = Path(__file__).parent.parent / "public" / "thumbnails"
thumbnails_dir.mkdir(parents=True, exist_ok=True)
app.mount("/thumbnails", StaticFiles(directory=str(thumbnails_dir)), name="thumbnails")


@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "YouTube Maker API", "status": "running"}


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.on_event("startup")
async def startup():
    """Startup event handler."""
    print("🚀 Application starting up...")


@app.on_event("shutdown")
async def shutdown():
    """Shutdown event handler."""
    print("👋 Application shutting down...")
    await engine.dispose()

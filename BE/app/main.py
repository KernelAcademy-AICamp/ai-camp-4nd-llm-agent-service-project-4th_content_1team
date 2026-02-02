import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

logging.basicConfig(level=logging.INFO)

from app.core.config import settings
from app.core.db import engine
from app.api.routes import auth, youtube, competitor, subtitle, persona, recommendations

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

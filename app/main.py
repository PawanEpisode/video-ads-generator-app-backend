from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from fastapi.staticfiles import StaticFiles
import os
from pathlib import Path
from .core.config import settings
from .api.endpoints.url_to_video import router as url_to_video_router

# Create necessary directories
BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"
VIDEOS_DIR = BASE_DIR / "output"

# Create directories if they don't exist
STATIC_DIR.mkdir(exist_ok=True)
VIDEOS_DIR.mkdir(exist_ok=True)

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="""
    Video Ads Generator API - A powerful tool for generating video ads from product pages.
    
    ## Features
    * Product information extraction from Shopify stores
    * Video generation from product data
    * Status tracking for video generation jobs
    * URL to Video conversion with AI-powered script generation
    
    ## API Endpoints
    * `/analyze-url` - Extract product information from a URL
    * `/generate-video` - Generate a video ad from product data
    * `/video-status/{job_id}` - Check video generation status
    * `/process-url` - Convert product URL to video ad scripts
    """,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=None,  # Disable default docs
    redoc_url=None  # Disable default redoc
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
app.mount("/videos", StaticFiles(directory=str(VIDEOS_DIR)), name="videos")

# Include routers
app.include_router(
    url_to_video_router,
    prefix=f"{settings.API_V1_STR}/url-to-video",
    tags=["url-to-video"]
)

@app.get("/")
async def root():
    return {
        "message": "Welcome to Video Ads Generator API",
        "version": settings.VERSION,
        "docs_url": "/docs"
    }

@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    return get_swagger_ui_html(
        openapi_url=f"{settings.API_V1_STR}/openapi.json",
        title=f"{settings.PROJECT_NAME} - API Documentation",
        swagger_js_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.9.0/swagger-ui-bundle.js",
        swagger_css_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.9.0/swagger-ui.css",
    )

def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    
    # Add security schemes if needed
    # openapi_schema["components"]["securitySchemes"] = {...}
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi 
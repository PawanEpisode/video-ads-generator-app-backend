from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from .core.config import settings
from .api.routes.scraper import router as scraper_router
from .api.routes.product import router as product_router

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="""
    Video Ads Generator API - A powerful tool for generating video ads from product pages.
    
    ## Features
    * Product information extraction from Shopify stores
    * Video generation from product data
    * Status tracking for video generation jobs
    
    ## API Endpoints
    * `/analyze-url` - Extract product information from a URL
    * `/generate-video` - Generate a video ad from product data
    * `/video-status/{job_id}` - Check video generation status
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

# Include routers
app.include_router(
    scraper_router,
    prefix=f"{settings.API_V1_STR}/scraper",
    tags=["scraper"]
)

app.include_router(
    product_router,
    prefix=f"{settings.API_V1_STR}/products",
    tags=["products"]
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
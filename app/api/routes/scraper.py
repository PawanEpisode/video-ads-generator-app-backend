from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, HttpUrl, Field
from typing import Optional, List, Dict, Any
from app.services.scraper.shopify import ShopifyScraper
from app.services.scraper.base import BaseScraper
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

class URLInput(BaseModel):
    """Input model for URL analysis requests."""
    url: HttpUrl = Field(
        ...,
        description="The URL of the product to analyze",
        example="https://shopify.supply/products/get-ship-done-hat-2-1"
    )

class APIResponse(BaseModel):
    """Standard API response model."""
    status: str = Field(..., description="Response status (success/error)", example="success")
    message: str = Field(..., description="Response message", example="Product information extracted successfully")
    data: Optional[Dict[str, Any]] = Field(None, description="Response data")

    class Config:
        schema_extra = {
            "example": {
                "status": "success",
                "message": "Operation completed successfully",
                "data": {}
            }
        }

class ProductData(BaseModel):
    """Model representing extracted product information."""
    title: str = Field(..., description="Product title", example="Get Ship Done Hat 2.0")
    description: str = Field("", description="Product description", example="Push to prod in style with the Get Ship Done Hat 2.0")
    price: float = Field(0.0, description="Product price", example=15.00)
    currency: str = Field("USD", description="Price currency", example="USD")
    status: str = Field("", description="Product status (e.g., available, sold out, retired)", example="Sold out")
    images: List[str] = Field(default_factory=list, description="List of product image URLs")
    features: List[str] = Field(default_factory=list, description="List of product features")
    brand: str = Field("", description="Product brand", example="Shopify Supply")
    variants: List[Dict[str, Any]] = Field(default_factory=list, description="Product variants")
    videos: List[Dict[str, Any]] = Field(default_factory=list, description="List of product video media (src, poster, alt)")

    class Config:
        schema_extra = {
            "example": {
                "title": "Get Ship Done Hat 2.0",
                "description": "Push to prod in style with the Get Ship Done Hat 2.0",
                "price": 15.00,
                "currency": "USD",
                "status": "Sold out",
                "images": [
                    "https://cdn.shopify.com/s/files/1/0000/0000/products/hat.jpg"
                ],
                "features": [
                    "100% cotton twill",
                    "Adjustable strap with metal buckle"
                ],
                "brand": "Shopify Supply",
                "variants": [],
                "videos": [
                    {
                        "src": "https://cdn.shopify.com/oxygen-v2/25850/10228/21102/1915254/assets/collection-entrepreneur-essentials-video-DBv33N9g.mp4",
                        "poster": "https://cdn.shopify.com/oxygen-v2/25850/10228/21102/1915254/assets/collection-entrepreneur-essentials-min-DrPrTYOl.jpg",
                        "alt": "Entrepreneur Essentials Collection"
                    }
                ]
            }
        }

class ProductResponse(APIResponse):
    """Response model for product data."""
    data: Optional[ProductData] = Field(None, description="Extracted product data")

    class Config:
        schema_extra = {
            "example": {
                "status": "success",
                "message": "Product information extracted successfully",
                "data": {
                    "title": "Get Ship Done Hat 2.0",
                    "description": "Push to prod in style with the Get Ship Done Hat 2.0",
                    "price": 15.00,
                    "currency": "USD",
                    "status": "Sold out",
                    "images": [
                        "https://cdn.shopify.com/s/files/1/0000/0000/products/hat.jpg"
                    ],
                    "features": [
                        "100% cotton twill",
                        "Adjustable strap with metal buckle"
                    ],
                    "brand": "Shopify Supply",
                    "variants": [],
                    "videos": [
                        {
                            "src": "https://cdn.shopify.com/oxygen-v2/25850/10228/21102/1915254/assets/collection-entrepreneur-essentials-video-DBv33N9g.mp4",
                            "poster": "https://cdn.shopify.com/oxygen-v2/25850/10228/21102/1915254/assets/collection-entrepreneur-essentials-min-DrPrTYOl.jpg",
                            "alt": "Entrepreneur Essentials Collection"
                        }
                    ]
                }
            }
        }

class VideoGenerationRequest(BaseModel):
    """Input model for video generation requests."""
    url: HttpUrl = Field(
        ...,
        description="The URL of the product to generate video for",
        example="https://shopify.supply/products/get-ship-done-hat-2-1"
    )
    style: Optional[str] = Field(
        "modern",
        description="Video style preference",
        example="modern"
    )

    class Config:
        schema_extra = {
            "example": {
                "url": "https://shopify.supply/products/get-ship-done-hat-2-1",
                "style": "modern"
            }
        }

class VideoStatus(BaseModel):
    """Model representing video generation status."""
    status: str = Field(..., description="Video generation status", example="processing")
    progress: Optional[int] = Field(None, description="Generation progress percentage", example=50)
    estimated_time: Optional[str] = Field(None, description="Estimated time remaining", example="2 minutes")

    class Config:
        schema_extra = {
            "example": {
                "status": "processing",
                "progress": 50,
                "estimated_time": "2 minutes"
            }
        }

class VideoStatusResponse(APIResponse):
    """Response model for video status."""
    data: Optional[VideoStatus] = Field(None, description="Video generation status")

    class Config:
        schema_extra = {
            "example": {
                "status": "success",
                "message": "Video status retrieved successfully",
                "data": {
                    "status": "processing",
                    "progress": 50,
                    "estimated_time": "2 minutes"
                }
            }
        }

@router.post("/analyze-url", response_model=ProductResponse, tags=["scraper"])
async def analyze_url(input_data: URLInput):
    """
    Analyze a product URL and extract relevant information.
    
    This endpoint extracts product information from a Shopify store URL, including:
    - Product title
    - Description
    - Price and currency
    - Availability status
    - Images
    - Features
    - Brand information
    - Product variants
    
    Returns a standardized API response with the extracted product data.
    """
    try:
        # Initialize the appropriate scraper
        scraper: BaseScraper = ShopifyScraper()
        
        if not scraper.can_handle_url(str(input_data.url)):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unsupported URL format. Currently only Shopify stores are supported."
            )

        # Extract product information
        product_data = await scraper.extract_product_info(str(input_data.url))
        
        # Validate the extracted data
        validated_data = ProductData(**product_data)
        
        return ProductResponse(
            status="success",
            message="Product information extracted successfully",
            data=validated_data
        )
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error analyzing URL: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to analyze URL: {str(e)}"
        )

@router.post("/generate-video", response_model=APIResponse, tags=["scraper"])
async def generate_video(request: VideoGenerationRequest):
    """
    Generate a video ad from the analyzed URL content.
    
    This endpoint initiates the video generation process for a product.
    It returns a job ID that can be used to track the video generation status.
    """
    try:
        # TODO: Implement video generation logic
        return APIResponse(
            status="success",
            message="Video generation started",
            data={"job_id": "sample-job-id"}
        )
    except Exception as e:
        logger.error(f"Error generating video: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate video: {str(e)}"
        )

@router.get("/video-status/{job_id}", response_model=VideoStatusResponse, tags=["scraper"])
async def get_video_status(job_id: str):
    """
    Check the status of a video generation job.
    
    This endpoint returns the current status of a video generation job,
    including progress percentage and estimated time remaining.
    """
    try:
        # TODO: Implement status check logic
        status_data = VideoStatus(
            status="processing",
            progress=50,
            estimated_time="2 minutes"
        )
        
        return VideoStatusResponse(
            status="success",
            message="Video status retrieved successfully",
            data=status_data
        )
    except Exception as e:
        logger.error(f"Error checking video status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check video status: {str(e)}"
        )

@router.get("/test-scrape/{url:path}", response_model=ProductResponse, tags=["scraper"])
async def test_scrape(url: str):
    """
    Test endpoint to see raw scraped values.
    
    This endpoint is for testing purposes and returns both the raw scraped data
    and the validated data structure. It's useful for debugging and development.
    """
    try:
        # Initialize the scraper
        scraper: BaseScraper = ShopifyScraper()
        
        # Ensure URL has proper scheme
        if not url.startswith(('http://', 'https://')):
            url = f"https://{url}"
        
        if not scraper.can_handle_url(url):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unsupported URL format. Currently only Shopify stores are supported."
            )

        # Extract product information
        product_data = await scraper.extract_product_info(url)
        
        # Validate the extracted data
        validated_data = ProductData(**product_data)
        
        return ProductResponse(
            status="success",
            message="Product information extracted successfully",
            data=validated_data
        )
    except Exception as e:
        logger.error(f"Error in test scrape: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to scrape URL: {str(e)}"
        ) 
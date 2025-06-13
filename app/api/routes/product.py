from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, List
from pydantic import BaseModel, HttpUrl
from ...services.scraper.shopify import ShopifyScraper
from ...services.scraper.base import BaseScraper

router = APIRouter()

class ProductURL(BaseModel):
    url: HttpUrl

class ProductInfo(BaseModel):
    title: str
    description: str
    price: float
    images: List[str]
    features: List[str]
    brand: str

@router.post("/scrape", response_model=ProductInfo)
async def scrape_product(url_data: ProductURL):
    """
    Scrape product information from the given URL.
    Currently supports Shopify stores.
    """
    url = str(url_data.url)
    
    # Initialize scrapers
    scrapers: List[BaseScraper] = [
        ShopifyScraper(),
        # Add more scrapers here as they are implemented
    ]
    
    # Find the appropriate scraper
    scraper = next((s for s in scrapers if s.can_handle_url(url)), None)
    
    if not scraper:
        raise HTTPException(
            status_code=400,
            detail="Unsupported product URL. Currently only Shopify stores are supported."
        )
    
    try:
        product_info = await scraper.extract_product_info(url)
        return ProductInfo(**product_info)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to scrape product information: {str(e)}"
        ) 
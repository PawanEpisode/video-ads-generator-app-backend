from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from bs4 import BeautifulSoup
import aiohttp
import asyncio
from app.core.config import settings
import logging
import re

logger = logging.getLogger(__name__)

class BaseScraper(ABC):
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        self.timeout = settings.SCRAPING_TIMEOUT
        self.max_retries = settings.MAX_RETRIES

    async def fetch_page(self, url: str) -> Optional[str]:
        """Fetch a page's content."""
        try:
            logger.info(f"Fetching page: {url}")
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=self.headers) as response:
                    if response.status != 200:
                        logger.error(f"Failed to fetch page: HTTP {response.status}")
                        return None
                    content = await response.text()
                    logger.info(f"Successfully fetched page content, length: {len(content)}")
                    return content
        except Exception as e:
            logger.error(f"Error fetching page: {str(e)}")
            return None

    @abstractmethod
    async def extract_product_info(self, url: str) -> Dict:
        """
        Extract product information from the given URL.
        Returns a dictionary containing:
        - title: str
        - description: str
        - price: float
        - images: List[str]
        - features: List[str]
        - brand: str
        """
        pass

    @abstractmethod
    def can_handle_url(self, url: str) -> bool:
        """Check if this scraper can handle the given URL."""
        pass

    def parse_html(self, html: str) -> Optional[BeautifulSoup]:
        """Parse HTML content."""
        try:
            if not isinstance(html, str):
                logger.warning(f"HTML content is not a string, converting...")
                html = str(html)
            
            logger.info("Parsing HTML content")
            soup = BeautifulSoup(html, 'html.parser')
            logger.info("Successfully parsed HTML")
            return soup
        except Exception as e:
            logger.error(f"Error parsing HTML: {str(e)}")
            return None

    async def download_image(self, image_url: str) -> Optional[bytes]:
        """Download an image from the given URL."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(image_url, headers=self.headers) as response:
                    if response.status == 200:
                        return await response.read()
        except Exception:
            return None
        return None 
from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from bs4 import BeautifulSoup
import aiohttp
import asyncio
from app.core.config import settings

class BaseScraper(ABC):
    def __init__(self):
        self.headers = {
            "User-Agent": settings.USER_AGENT
        }
        self.timeout = settings.SCRAPING_TIMEOUT
        self.max_retries = settings.MAX_RETRIES

    async def fetch_page(self, url: str) -> Optional[str]:
        """Fetch the webpage content with retries."""
        for attempt in range(self.max_retries):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, headers=self.headers, timeout=self.timeout) as response:
                        if response.status == 200:
                            return await response.text()
                        elif response.status == 429:  # Too Many Requests
                            await asyncio.sleep(2 ** attempt)  # Exponential backoff
                        else:
                            return None
            except Exception as e:
                if attempt == self.max_retries - 1:
                    raise e
                await asyncio.sleep(2 ** attempt)
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

    def parse_html(self, html: str) -> BeautifulSoup:
        """Parse HTML content using BeautifulSoup."""
        return BeautifulSoup(html, 'lxml')

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
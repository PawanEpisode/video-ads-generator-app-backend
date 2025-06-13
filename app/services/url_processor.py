from typing import Dict, Optional
import aiohttp
from bs4 import BeautifulSoup
import json
import logging
from .scraper.shopify import ShopifyScraper
from .scraper.base import BaseScraper
from app.core.config import settings
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)

class URLProcessor:
    def __init__(self):
        self.scraper = ShopifyScraper()
        self.logger = logging.getLogger(__name__)
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    async def fetch_url_content(self, url: str) -> Dict:
        """Fetch and extract content from a URL."""
        try:
            self.logger.info(f"Fetching content from URL: {url}")
            # Use the scraper to get product data
            product_data = await self.scraper.extract_product_info(url)
            self.logger.info(f"Scraped product data: {product_data}")
            
            # Transform the data into the required format
            transformed_data = {
                "title": product_data.get("title", ""),
                "description": product_data.get("description", ""),
                "features": product_data.get("features", []),
                "images": product_data.get("images", []),
                "videos": product_data.get("videos", []),
                "price": str(product_data.get("price", "")),
                "brand": product_data.get("brand", "")
            }
            
            self.logger.info(f"Transformed data: {transformed_data}")
            return transformed_data
        except Exception as e:
            self.logger.error(f"Error fetching URL content: {str(e)}")
            raise Exception(f"Error fetching URL content: {str(e)}")

    async def generate_ad_script(self, product_data: Dict) -> Dict:
        """Generate an ad script using OpenAI."""
        try:
            self.logger.info("Generating ad script with product data")
            
            # Create a prompt for the ad script
            prompt = f"""Create a compelling 30-second video ad script for the following product:

Title: {product_data['title']}
Description: {product_data['description']}
Features: {', '.join(product_data['features'])}
Price: {product_data['price']}
Brand: {product_data['brand']}

The script should:
1. Be engaging and persuasive
2. Highlight key features and benefits
3. Include a clear call to action
4. Be suitable for a 30-second video
5. Follow this exact format:

First, include a header section with product details:
**Title:** [Product Title]
**Description:** [Product Description]
**Features:** [List of Features]
**Price:** [Price]
**Brand:** [Brand]

Then, after a line with just "---", include the scenes with timestamps:
[0:00] *[Scene description]*
[0:05] *[Next scene description]*
[0:10] *[Next scene description]*
And so on...

Each scene should be 5 seconds long, and the total video should be 30 seconds.
Make sure to use asterisks (*) around scene descriptions."""

            # Generate the script using OpenAI
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a professional advertising copywriter specializing in creating compelling video ad scripts."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=500
            )

            # Extract the generated script
            script_content = response.choices[0].message.content
            self.logger.info(f"Generated script: {script_content}")

            return {
                "content": script_content,
                "variations": []  # We'll keep this for future use
            }
        except Exception as e:
            self.logger.error(f"Error generating ad script: {str(e)}")
            raise Exception(f"Error generating ad script: {str(e)}")

    async def process_url(self, url: str) -> Dict:
        """Process a URL and generate video ad content."""
        try:
            self.logger.info(f"Processing URL: {url}")
            # Fetch product data
            product_data = await self.fetch_url_content(url)
            self.logger.info(f"Fetched product data: {product_data}")
            
            # Generate ad script
            script = await self.generate_ad_script(product_data)
            self.logger.info(f"Generated script: {script}")
            
            return {
                "product_data": product_data,
                "script": script
            }
        except Exception as e:
            self.logger.error(f"Error processing URL: {str(e)}")
            raise Exception(f"Error processing URL: {str(e)}") 
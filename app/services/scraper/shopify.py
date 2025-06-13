from typing import Dict, List, Optional
import re
from .base import BaseScraper
import logging
from playwright.async_api import async_playwright

logger = logging.getLogger(__name__)

class ShopifyScraper(BaseScraper):
    def can_handle_url(self, url: str) -> bool:
        """Check if the URL is from a Shopify store."""
        # Common Shopify store patterns
        patterns = [
            r'\.myshopify\.com',
            r'\.myshopify\.io',
            r'\.myshopify\.store',
            r'shopify\.supply',
            r'\.myshopify\.co',
            r'\.myshopify\.shop',
            r'\.myshopify\.site',
            r'\.myshopify\.net',
            r'\.myshopify\.app',
            r'\.myshopify\.dev',
            r'\.myshopify\.test',
            r'\.myshopify\.local',
            r'\.myshopify\.dev\.shopify\.com',
            r'\.myshopify\.com\/admin',
            r'\.myshopify\.com\/products',
            r'\.myshopify\.com\/collections',
            r'\.myshopify\.com\/blogs',
            r'\.myshopify\.com\/pages',
            r'\.myshopify\.com\/search',
            r'\.myshopify\.com\/cart',
            r'\.myshopify\.com\/checkout',
            r'\.myshopify\.com\/account',
        ]
        return any(re.search(pattern, url) for pattern in patterns)

    async def fetch_page_playwright(self, url: str, timeout: int = 30000) -> str:
        """Fetch page content using Playwright for dynamic content."""
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                
                # Set viewport size
                await page.set_viewport_size({"width": 1920, "height": 1080})
                
                # Navigate to the page and wait for network idle
                await page.goto(url, wait_until="networkidle", timeout=timeout)
                
                # Wait for any dynamic content to load
                await page.wait_for_load_state("domcontentloaded")
                
                # Get the page content
                content = await page.content()
                
                # Close browser
                await browser.close()
                
                return content
        except Exception as e:
            logger.error(f"Error fetching page with Playwright: {str(e)}")
            return ""

    async def extract_product_info(self, url: str, use_playwright: bool = True) -> Dict:
        """Extract product information from a Shopify store."""
        try:
            # Use Playwright for dynamic content by default
            if use_playwright:
                html = await self.fetch_page_playwright(url)
            else:
                html = await self.fetch_page(url)
                
            if not html:
                raise ValueError("Failed to fetch the product page")

            soup = self.parse_html(html)
            
            # Extract product information
            product_data = {
                "title": self._extract_title(soup),
                "description": self._extract_description(soup),
                "price": self._extract_price(soup),
                "images": self._extract_images(soup),
                "features": self._extract_features(soup),
                "brand": self._extract_brand(soup),
                "status": self._extract_status(soup),
                "variants": self._extract_variants(soup),
                "currency": self._extract_currency(soup),
                "videos": self._extract_videos(soup)
            }
            
            # Log the extracted data for debugging
            logger.debug(f"Extracted product data: {product_data}")
            
            return product_data
        except Exception as e:
            logger.error(f"Error extracting product info: {str(e)}")
            raise

    def _extract_title(self, soup) -> str:
        """Extract product title."""
        # Try multiple selectors for product title
        selectors = [
            'header h2.text-h2',  # Primary selector for your case
            'h2[class*="text-h2"]',  # Alternative for your case
            'header h2',  # Fallback
            'h1.product-title',
            'h1.product-single__title',
            'h1.product__title',
            'h1.product-name',
            'h1[class*="product"]',
            'h1[class*="title"]',
            'h1'  # Last resort
        ]
        
        for selector in selectors:
            title_elem = soup.select_one(selector)
            if title_elem and title_elem.text.strip():
                return title_elem.text.strip()
        
        return ""

    def _extract_description(self, soup) -> str:
        """Extract product description."""
        selectors = [
            'div.product-accordion-panel div.pb-7',  # Primary selector for your case
            'div.product-accordion-panel p',  # Alternative for your case
            'div.product-description',
            'div.product-single__description',
            'div.product__description',
            'div[id="product-description"]',
            'div.product-description__content',
            'div.product-description__body',
            'div[class*="description"]',
            'div[class*="content"]',
            'meta[name="description"]'
        ]
        
        for selector in selectors:
            desc_elem = soup.select_one(selector)
            if desc_elem:
                if selector == 'meta[name="description"]':
                    return desc_elem.get('content', '').strip()
                
                # For div containers, get all paragraphs
                if selector in ['div.product-accordion-panel div.pb-7', 'div.product-description', 
                              'div.product-single__description', 'div.product__description']:
                    paragraphs = desc_elem.find_all('p')
                    if paragraphs:
                        # Join all paragraph texts with newlines
                        return '\n\n'.join(p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True))
                
                # For other cases, just get the text
                return desc_elem.get_text(strip=True)
        
        return ""

    def _extract_price(self, soup) -> float:
        """Extract product price."""
        selectors = [
            'div.flex.items-center span.text-h3',  # Primary selector for your case
            'div.flex.flex-col span.text-h3',  # Alternative for your case
            'span.text-h3',  # Simple text-h3 selector
            'span.text-h5',  # Previous selector
            'span[class*="text-h5"]',
            'span[class*="text-h3"]',
            'span[class*="price"]',
            'div[class*="price"]',
            'span.product-price',
            'span.product__price',
            'span[data-product-price]',
            'span.price-item--regular',
            'span.price-item--sale',
            'meta[property="product:price:amount"]'
        ]
        
        for selector in selectors:
            price_elem = soup.select_one(selector)
            if price_elem:
                if selector == 'meta[property="product:price:amount"]':
                    price_text = price_elem.get('content', '')
                else:
                    price_text = price_elem.text.strip()
                
                # Extract numeric price using regex
                # Updated regex to handle currency symbols and formats
                price_match = re.search(r'[\d,.]+', price_text)
                if price_match:
                    try:
                        # Remove currency symbols and commas, then convert to float
                        price_str = price_match.group().replace(',', '')
                        return float(price_str)
                    except ValueError:
                        continue
        
        return 0.0

    def _extract_images(self, soup) -> List[str]:
        """Extract product images, including from swiper-wrapper/swiper-slide structures and srcset attributes."""
        images = set()

        # Existing selectors
        selectors = [
            'div.product-image img',
            'div.product-single__photo img',
            'div.product__photo img',
            'div[data-product-image] img',
            'div.product-gallery__image img',
            'div.product-media img',
            'img[class*="product"]',
            'img[data-product-image]',
            'meta[property="og:image"]',
            'img',  # catch-all for any img
        ]

        for selector in selectors:
            elements = soup.select(selector)
            for elem in elements:
                # Prefer highest resolution from srcset
                srcset = elem.get('srcset')
                if srcset:
                    # srcset is a comma-separated list of URLs and widths
                    candidates = [s.strip() for s in srcset.split(',')]
                    max_width = 0
                    best_url = None
                    for candidate in candidates:
                        parts = candidate.split(' ')
                        if len(parts) == 2 and parts[1].endswith('w'):
                            try:
                                width = int(parts[1][:-1])
                                if width > max_width:
                                    max_width = width
                                    best_url = parts[0]
                            except Exception:
                                continue
                        elif len(parts) == 1:
                            # Sometimes srcset is just a list of URLs
                            best_url = parts[0]
                    if best_url:
                        images.add(best_url)
                        continue
                # Fallback to src or content
                src = elem.get('src') or elem.get('content')
                if src:
                    if src.startswith('//'):
                        src = f"https:{src}"
                    elif src.startswith('/'):
                        src = f"https://{self.base_url}{src}" if hasattr(self, 'base_url') else src
                    if 'cdn.shopify.com' in src:
                        src = re.sub(r'_\d+x\d+', '', src)
                    images.add(src)

        # Extract images from swiper-wrapper/swiper-slide structure
        swiper_slides = soup.select('div.swiper-wrapper div.swiper-slide a[href]')
        for a_tag in swiper_slides:
            href = a_tag.get('href')
            if href and href.startswith('http') and 'cdn.shopify.com' in href:
                images.add(href)

        return list(images)

    def _extract_features(self, soup) -> List[str]:
        """Extract product features."""
        features = set()
        
        # Look for features in various common locations
        selectors = [
            'ul.product-features li',
            'div.product-features li',
            'div[id="product-features"] li',
            'div.product__features li',
            'div.product-features__list li',
            'div[class*="features"] li',
            'div[class*="specifications"] li',
            'div[class*="details"] li'
        ]
        
        for selector in selectors:
            elements = soup.select(selector)
            features.update([elem.text.strip() for elem in elements if elem.text.strip()])
        
        return list(features)

    def _extract_brand(self, soup) -> str:
        """Extract product brand."""
        selectors = [
            'div.product-brand',
            'span.product-brand',
            'a.product-brand',
            'div.product__brand',
            'span.product__brand',
            'a.product__brand',
            'meta[property="product:brand"]',
            'div[class*="brand"]',
            'span[class*="brand"]'
        ]
        
        for selector in selectors:
            brand_elem = soup.select_one(selector)
            if brand_elem:
                if selector == 'meta[property="product:brand"]':
                    return brand_elem.get('content', '').strip()
                return brand_elem.text.strip()
        
        return ""

    def _extract_status(self, soup) -> str:
        """Extract product status (e.g., retired, sold out, etc.)."""
        selectors = [
            'span.inline-block span',  # Primary selector for your case
            'span[class*="inline-block"] span',  # Alternative for your case
            'span[class*="status"]',
            'div[class*="status"]',
            'span[class*="badge"]',
            'div[class*="badge"]',
            'span[class*="tag"]',
            'div[class*="tag"]',
            'span[class*="sold-out"]',
            'div[class*="sold-out"]',
            'span[class*="availability"]',
            'div[class*="availability"]'
        ]
        
        for selector in selectors:
            status_elem = soup.select_one(selector)
            if status_elem and status_elem.text.strip():
                return status_elem.text.strip()
        
        return ""

    def _extract_variants(self, soup) -> List[Dict]:
        """Extract product variants."""
        variants = []
        
        # Look for variant selectors
        variant_selectors = [
            'select[data-product-select] option',
            'select[data-product-options] option',
            'select[class*="variant"] option',
            'div[class*="variant"] input[type="radio"]'
        ]
        
        for selector in variant_selectors:
            elements = soup.select(selector)
            for elem in elements:
                variant = {
                    "name": elem.text.strip(),
                    "value": elem.get('value', ''),
                    "selected": elem.get('selected') == 'selected' or elem.get('checked') == 'checked'
                }
                if variant["name"] and variant["value"]:
                    variants.append(variant)
        
        return variants

    def _extract_currency(self, soup) -> str:
        """Extract product currency."""
        selectors = [
            'span[class*="text-h3"]',  # Primary selector for your case
            'span[class*="price"]',
            'div[class*="price"]',
            'meta[property="product:price:currency"]'
        ]
        
        for selector in selectors:
            elem = soup.select_one(selector)
            if elem:
                if selector == 'meta[property="product:price:currency"]':
                    return elem.get('content', '')
                else:
                    # Extract currency from price text
                    text = elem.text.strip()
                    # Look for common currency symbols or codes
                    currency_match = re.search(r'([A-Z]{3}|\$|€|£|¥)', text)
                    if currency_match:
                        return currency_match.group()
        
        return "USD"  # Default to USD if no currency found 

    def _extract_videos(self, soup) -> list:
        """Extract video media from product/collection pages, especially inside swiper-slide."""
        videos = []
        # Find all <video> tags inside swiper-slide
        for video_tag in soup.select('div.swiper-slide video'):
            video_info = {}
            # Try <source src=...>
            source_tag = video_tag.find('source')
            if source_tag and source_tag.get('src'):
                video_info['src'] = source_tag['src']
            elif video_tag.get('src'):
                video_info['src'] = video_tag['src']
            else:
                continue  # skip if no video source
            # Poster image
            if video_tag.get('poster'):
                video_info['poster'] = video_tag['poster']
            # Alt text
            if video_tag.get('alt'):
                video_info['alt'] = video_tag['alt']
            else:
                parent_a = video_tag.find_parent('a')
                if parent_a and parent_a.get('alt'):
                    video_info['alt'] = parent_a['alt']
                else:
                    h5 = video_tag.find_next('h5')
                    if h5 and h5.text:
                        video_info['alt'] = h5.text.strip()
            videos.append(video_info)
        logger.debug(f"Extracted videos: {videos}")
        return videos 
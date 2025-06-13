# Video Ads Generator Backend

## Architecture Overview

### Tech Stack

- FastAPI: Modern, fast web framework for building APIs
- BeautifulSoup4: Web scraping
- OpenAI API: Content generation
- MoviePy: Video generation
- SQLAlchemy: Database ORM
- Pydantic: Data validation
- Celery: Background task processing

### Project Structure

```
backend/
├── app/
│   ├── api/
│   │   ├── routes/
│   │   │   ├── product.py
│   │   │   ├── video.py
│   │   │   └── ai.py
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   └── security.py
│   │   ├── services/
│   │   │   ├── scraper/
│   │   │   │   ├── base.py
│   │   │   │   ├── shopify.py
│   │   │   │   └── amazon.py
│   │   │   ├── ai/
│   │   │   │   ├── openai_service.py
│   │   │   │   └── content_generator.py
│   │   │   └── video/
│   │   │       ├── video_generator.py
│   │   │       └── templates/
│   │   ├── models/
│   │   │   ├── product.py
│   │   │   └── video.py
│   │   └── schemas/
│   │       ├── product.py
│   │       └── video.py
│   ├── tests/
│   └── requirements.txt
```

## Implementation Plan

### Phase 1: URL Scraping & Data Extraction

1. Implement base scraper interface
2. Create platform-specific scrapers (Shopify, Amazon)
3. Implement data validation and storage
4. Add error handling and rate limiting

### Phase 2: AI Content Generation

1. Set up OpenAI integration
2. Implement content generation service
3. Create script variations
4. Add content optimization

### Phase 3: Video Generation

1. Set up video generation service
2. Implement template system
3. Add text overlay and animations
4. Support multiple aspect ratios

## API Endpoints

### Product Scraping

- `POST /api/v1/products/scrape`
  - Input: URL
  - Output: Product details (images, description, features)

### Content Generation

- `POST /api/v1/content/generate`
  - Input: Product details
  - Output: Generated ad copy and scripts

### Video Generation

- `POST /api/v1/videos/generate`
  - Input: Content and product details
  - Output: Video URL

## Best Practices

### API Design

- RESTful endpoints
- Version control (v1)
- Proper error handling
- Rate limiting
- Input validation
- Documentation (OpenAPI/Swagger)

### Security

- API key authentication
- CORS configuration
- Input sanitization
- Rate limiting
- Secure file handling

### Performance

- Async operations
- Background task processing
- Caching
- Resource optimization

### Scalability

- Modular design
- Service separation
- Background task processing
- Database optimization

## Getting Started

1. Set up virtual environment:

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Set up environment variables:

```bash
cp .env.example .env
# Edit .env with your configuration
```

4. Run the development server:

```bash
uvicorn app.main:app --reload
```

## Development Guidelines

1. Follow PEP 8 style guide
2. Write unit tests for new features
3. Document API endpoints
4. Use type hints
5. Implement proper error handling
6. Follow Git flow branching strategy

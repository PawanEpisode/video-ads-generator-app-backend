# Video Ads Generator Backend

A FastAPI-based backend for the Video Ads Generator application that processes product URLs and generates video advertisements.

## Features

- URL analysis and content extraction
- Video generation pipeline
- OpenAI integration for content enhancement
- Asynchronous job processing

## Tech Stack

- FastAPI
- Python 3.8+
- OpenAI API
- BeautifulSoup4 for web scraping
- Uvicorn for ASGI server

## Setup Instructions

1. Create a virtual environment:

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Create a `.env` file in the backend directory with the following variables:

```
OPENAI_API_KEY=your_openai_api_key
```

4. Start the development server:

```bash
uvicorn app.main:app --reload
```

5. The API will be available at [http://localhost:8000](http://localhost:8000)

## API Documentation

Once the server is running, you can access:

- Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)
- ReDoc: [http://localhost:8000/redoc](http://localhost:8000/redoc)

## API Endpoints

- POST `/api/analyze-url` - Analyze product URL
- POST `/api/generate-video` - Generate video from analyzed content
- GET `/api/video-status/{job_id}` - Check video generation status

## Project Structure

```
backend/
├── app/
│   ├── api/          # API routes and endpoints
│   ├── core/         # Core configuration
│   ├── services/     # Business logic and services
│   └── main.py       # FastAPI application
├── requirements.txt  # Python dependencies
└── README.md        # This file
```

## Development

- Use `uvicorn app.main:app --reload` for development
- Use `uvicorn app.main:app` for production
- Use `pytest` for running tests (when implemented)

# Backend Documentation

## Overview

The backend is built with FastAPI and handles video generation from product images and descriptions. It uses OpenCV for image processing and FFmpeg for video encoding.

## Setup Instructions

### Prerequisites

1. **System Requirements**

   - Python 3.8 or higher
   - FFmpeg installed on your system
   - Git
   - Virtual environment tool (venv or conda)

2. **Install FFmpeg**
   - **macOS**:
     ```bash
     brew install ffmpeg
     ```
   - **Ubuntu/Debian**:
     ```bash
     sudo apt update
     sudo apt install ffmpeg
     ```
   - **Windows**:
     - Download from [FFmpeg official website](https://ffmpeg.org/download.html)
     - Add to system PATH

### Installation Steps

1. **Clone the Repository**

   ```bash
   git clone https://github.com/PawanEpisode/video-ads-generator-app-backend.git
   cd video-ads-generator-app/backend
   ```

2. **Create and Activate Virtual Environment**

   ```bash
   # Using venv
   python3 -m venv venv

   # Activate virtual environment
   # On macOS/Linux:
   source venv/bin/activate
   # On Windows:
   .\venv\Scripts\activate
   ```

3. **Install Dependencies**

   ```bash
   pip3 install -r requirements.txt
   ```

4. **Set Up Environment Variables**

   ```bash
   # Create .env file
   touch .env

   copy the env variables from .env.example file
   ```
   # Note: OpenAI API Key Setup
   - Create an account on [OpenAI](https://platform.openai.com/signup)
   - Once logged in, go to [API Keys](https://platform.openai.com/api-keys)
   - Click "Create new secret key"
   - Copy the generated API key (Note: You won't be able to see it again)
   - Add it to your .env file as `OPENAI_API_KEY=your_api_key_here`

5. **Create Required Directories**
   ```bash
   mkdir temp output
   ```

### Running the Application

1. **Start the Development Server**

   ```bash
   ./venv/bin/uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

2. **Verify Installation**
   - Open your browser and navigate to `http://localhost:8000/docs`
   - You should see the Swagger UI documentation
   - Test the health check endpoint at `http://localhost:8000/health`

### Common Issues and Solutions

1. **FFmpeg Not Found**

   - Verify FFmpeg installation:
     ```bash
     ffmpeg -version
     ```
   - If not found, ensure FFmpeg is in your system PATH

2. **Port Already in Use**

   - Change the port number:
     ```bash
     uvicorn app.main:app --reload --port 8001
     ```

3. **Permission Issues**

   - Ensure proper permissions for temp and output directories:
     ```bash
     chmod 755 temp output
     ```

4. **Virtual Environment Issues**
   - If you get "command not found" errors, ensure the virtual environment is activated
   - You should see `(venv)` at the start of your command prompt

### Development Workflow

1. **Code Changes**

   - The server will automatically reload when you make changes
   - Check the console for any error messages

2. **Testing**

   ```bash
   # Run tests
   pytest

   # Run tests with coverage
   pytest --cov=app
   ```

3. **API Documentation**
   - Swagger UI: `http://localhost:8000/docs`
   - ReDoc: `http://localhost:8000/redoc`

## Architecture

### Core Components

1. **VideoGenerator Service**

   - Handles video generation from images and text
   - Manages temporary files and cleanup
   - Provides text overlay with proper formatting

2. **API Endpoints**
   - `/process`: Main endpoint for video generation
   - `/videos`: Serves generated videos
   - `/health`: Health check endpoint

### Key Features

1. **Image Processing**

   - Downloads and validates images
   - Handles various image formats
   - Maintains aspect ratio during resizing
   - Supports both local and remote image URLs

2. **Text Overlay**

   - Dynamic text wrapping
   - Centered text positioning
   - Semi-transparent background
   - Proper line spacing and padding

3. **Video Generation**
   - Configurable FPS and duration
   - H.264 encoding for web compatibility
   - Proper aspect ratio maintenance
   - Fallback mechanisms for errors

## Technical Details

### VideoGenerator Class

```python
class VideoGenerator:
    def __init__(self):
        # Video settings
        self.fps = 24
        self.duration_per_image = 5
        self.text_scale = 0.8
        self.text_thickness = 1
        self.text_padding = 20
```

### Key Methods

1. **download_media**

   - Downloads images from URLs
   - Handles CORS and network issues
   - Validates downloaded content
   - Creates fallback black screen if needed

2. **generate_video**

   - Creates video from images and text
   - Manages scene transitions
   - Handles video encoding
   - Provides progress updates

3. **\_create_text_overlay**
   - Implements text wrapping
   - Centers text in background
   - Positions overlay at bottom
   - Handles multi-line text

## Setup and Configuration

1. **Dependencies**

   ```
   fastapi
   opencv-python
   numpy
   aiohttp
   python-multipart
   ```

2. **FFmpeg Requirements**
   - Must be installed on the system
   - Used for video encoding
   - Supports H.264 codec

## Error Handling

1. **Image Processing**

   - Validates image downloads
   - Handles corrupt images
   - Provides fallback mechanisms

2. **Video Generation**

   - Validates input parameters
   - Handles encoding errors
   - Cleans up temporary files

3. **Text Overlay**
   - Handles text overflow
   - Manages font rendering
   - Provides fallback for missing fonts

## Performance Considerations

1. **Memory Management**

   - Cleans up temporary files
   - Manages image buffers
   - Handles large video files

2. **Async Operations**
   - Uses aiohttp for downloads
   - Implements proper async/await
   - Handles concurrent requests

## Security

1. **File Handling**

   - Validates file types
   - Sanitizes file paths
   - Implements proper cleanup

2. **API Security**
   - Input validation
   - Error message sanitization
   - Proper CORS handling

## Contributing

1. Follow PEP 8 style guide
2. Add proper error handling
3. Include docstrings
4. Update tests

## License

MIT License

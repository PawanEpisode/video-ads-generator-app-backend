import os
from moviepy.config import change_settings

# Get the current directory
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

# Try to find ImageMagick in common locations
IMAGEMAGICK_PATHS = [
    '/usr/bin/convert',  # Linux
    '/usr/local/bin/convert',  # macOS
    'C:\\Program Files\\ImageMagick-7.0.11-Q16\\convert.exe',  # Windows
    'C:\\Program Files\\ImageMagick-7.0.10-Q16\\convert.exe',  # Windows
    'C:\\Program Files\\ImageMagick-7.0.9-Q16\\convert.exe',  # Windows
]

def configure_moviepy():
    """Configure MoviePy settings."""
    # Check if ImageMagick exists in any of the common paths
    imagemagick_path = None
    for path in IMAGEMAGICK_PATHS:
        if os.path.exists(path):
            imagemagick_path = path
            break
    
    if imagemagick_path:
        # Set ImageMagick binary path
        change_settings({"IMAGEMAGICK_BINARY": imagemagick_path})
    else:
        # If ImageMagick is not found, use a fallback configuration
        change_settings({
            "IMAGEMAGICK_BINARY": None,
            "FFMPEG_BINARY": "ffmpeg",
            "IMAGEMAGICK_BINARY": None
        }) 
from pydantic import BaseModel, HttpUrl
from typing import Dict, List, Optional

class URLRequest(BaseModel):
    """Request model for URL processing."""
    url: str
    generate_video: bool = False

class VideoStatus(BaseModel):
    """Model for video generation status."""
    status: str
    progress: int
    message: Optional[str] = None
    error: Optional[str] = None
    video_path: Optional[str] = None

class VideoJob(BaseModel):
    """Model for video generation job info."""
    job_id: str
    status: str
    progress: int
    message: str
    video_path: Optional[str] = None

class URLResponse(BaseModel):
    """Response model for URL processing."""
    product_data: Dict
    script: Dict
    video_job: Optional[VideoJob] = None 
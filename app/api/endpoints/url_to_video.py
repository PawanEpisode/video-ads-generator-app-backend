from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from pydantic import BaseModel, HttpUrl
from typing import Dict, List, Optional
from app.services.url_processor import URLProcessor
from app.services.video_generator import VideoGenerator
import uuid
import os
from pathlib import Path
from fastapi.responses import FileResponse
from app.schemas.url_to_video import URLRequest, URLResponse, VideoStatus, VideoJob
import logging
import json

logger = logging.getLogger(__name__)

router = APIRouter()
url_processor = URLProcessor()
video_generator = VideoGenerator()

# Store video generation jobs
video_jobs: Dict[str, VideoJob] = {}

class URLRequest(BaseModel):
    url: HttpUrl
    generate_video: bool = False

class ScriptResponse(BaseModel):
    content: str
    duration: str
    type: str
    images: List[str]
    videos: List[Dict]

class ProductData(BaseModel):
    title: str
    description: str
    features: List[str]
    benefits: List[str]
    images: List[str]
    videos: List[Dict]
    price: float
    brand: str

class URLProcessResponse(BaseModel):
    product_data: ProductData
    ad_scripts: List[ScriptResponse]
    job_id: Optional[str] = None

@router.post("/process", response_model=URLResponse)
async def process_url(request: URLRequest, background_tasks: BackgroundTasks):
    """Process a URL and generate video ad content."""
    try:
        logger.info(f"Processing URL request: {request.dict()}")
        
        # Process the URL
        result = await url_processor.process_url(str(request.url))
        logger.info(f"URL processing result: {json.dumps(result, indent=2)}")
        
        # If video generation is requested, start the background task
        if request.generate_video:
            job_id = str(uuid.uuid4())
            logger.info(f"Creating video generation job with ID: {job_id}")
            
            # Initialize job status
            video_jobs[job_id] = VideoJob(
                job_id=job_id,
                status="processing",
                progress=0,
                message="Starting video generation..."
            )
            
            # Start video generation in background
            background_tasks.add_task(
                generate_video_task,
                job_id,
                result["product_data"],
                result["script"]
            )
            
            result["video_job"] = video_jobs[job_id]
        
        return result
    except Exception as e:
        logger.error(f"Error processing URL: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing URL: {str(e)}")

async def generate_video_task(job_id: str, product_data: Dict, script: Dict):
    """Background task for video generation."""
    try:
        logger.info(f"Starting video generation task for job {job_id}")
        
        # Update job status
        video_jobs[job_id].progress = 10
        video_jobs[job_id].message = "Downloading media files..."
        
        # Download media files
        media_files = await video_generator.download_media(product_data)
        logger.info(f"Downloaded media files: {media_files}")
        
        # Update job status
        video_jobs[job_id].progress = 50
        video_jobs[job_id].message = "Generating video..."
        
        # Generate video
        video_path = await video_generator.generate_video(script, media_files)
        logger.info(f"Generated video at: {video_path}")
        
        # Update job status
        video_jobs[job_id].status = "completed"
        video_jobs[job_id].progress = 100
        video_jobs[job_id].message = "Video generation completed"
        video_jobs[job_id].video_path = video_path
        
    except Exception as e:
        logger.error(f"Error in video generation task: {str(e)}")
        video_jobs[job_id].status = "failed"
        video_jobs[job_id].message = f"Video generation failed: {str(e)}"

@router.get("/video-status/{job_id}", response_model=VideoStatus)
async def get_video_status(job_id: str):
    """Get the status of a video generation job."""
    logger.info(f"Checking status for job {job_id}")
    if job_id not in video_jobs:
        logger.warning(f"Job {job_id} not found")
        raise HTTPException(status_code=404, detail="Job not found")
    return video_jobs[job_id]

@router.get("/video/{job_id}")
async def get_video(job_id: str):
    """Get the generated video file."""
    logger.info(f"Retrieving video for job {job_id}")
    if job_id not in video_jobs:
        logger.warning(f"Job {job_id} not found")
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = video_jobs[job_id]
    if job.status != "completed" or not job.video_path:
        logger.warning(f"Video not ready for job {job_id}")
        raise HTTPException(status_code=400, detail="Video not ready")
    
    return {"video_path": job.video_path} 
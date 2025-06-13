from typing import Dict, List, Optional
import os
from moviepy.editor import VideoFileClip, ImageClip, TextClip, CompositeVideoClip, AudioFileClip, ColorClip
from app.core.config import settings
import uuid
import aiohttp
import asyncio
from pathlib import Path
import logging
import tempfile
import shutil
from moviepy.editor import concatenate_videoclips
from moviepy.config import change_settings
from app.core.moviepy_config import configure_moviepy
from PIL import Image

logger = logging.getLogger(__name__)

class VideoGenerator:
    def __init__(self, logger=None):
        """Initialize the VideoGenerator."""
        self.logger = logger or logging.getLogger(__name__)
        
        # Set up directories
        self.base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.temp_dir = os.path.join(self.base_dir, 'temp')
        self.output_dir = os.path.join(self.base_dir, 'output')
        
        # Create directories if they don't exist
        for directory in [self.temp_dir, self.output_dir]:
            if not os.path.exists(directory):
                os.makedirs(directory, exist_ok=True)
                self.logger.info(f"Created directory: {directory}")
            else:
                self.logger.info(f"Using existing directory: {directory}")
        
        # Clean up any existing files in temp directory
        self._cleanup_temp_files()
        
        # Check for ffmpeg
        try:
            import subprocess
            result = subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True)
            if result.returncode != 0:
                raise Exception("ffmpeg command failed")
            self.logger.info("ffmpeg is installed and working")
        except Exception as e:
            self.logger.error("ffmpeg is not installed or not working")
            self.logger.error("Please install ffmpeg:")
            self.logger.error("  - On macOS: brew install ffmpeg")
            self.logger.error("  - On Ubuntu/Debian: sudo apt-get install ffmpeg")
            self.logger.error("  - On Windows: Download from https://ffmpeg.org/download.html")
            raise Exception("ffmpeg is required but not installed. Please install ffmpeg to generate videos.")
        
        # Configure MoviePy settings
        configure_moviepy()
        
        # Set fallback text rendering method
        self.use_simple_text = True  # Default to simple text rendering

    def _cleanup_temp_files(self):
        """Clean up temporary files from previous runs."""
        try:
            if os.path.exists(self.temp_dir):
                for file in os.listdir(self.temp_dir):
                    file_path = os.path.join(self.temp_dir, file)
                    try:
                        if os.path.isfile(file_path):
                            os.unlink(file_path)
                            self.logger.info(f"Cleaned up temporary file: {file}")
                    except Exception as e:
                        self.logger.warning(f"Error cleaning up file {file}: {str(e)}")
        except Exception as e:
            self.logger.error(f"Error cleaning up temporary files: {str(e)}")
            
    def cleanup(self):
        """Clean up resources after video generation."""
        try:
            self._cleanup_temp_files()
            self.logger.info("Cleanup completed successfully")
        except Exception as e:
            self.logger.error(f"Error during cleanup: {str(e)}")

    async def download_media(self, product_data: Dict) -> Dict[str, List[str]]:
        """Download all media files (images and videos) from product data."""
        try:
            self.logger.info("Starting media download")
            media_files = {
                "images": [],
                "videos": []
            }

            # Download images
            if product_data.get("images"):
                self.logger.info(f"Downloading {len(product_data['images'])} images")
                image_paths = await self._download_files(product_data["images"], "images")
                media_files["images"] = image_paths

            # Download videos
            if product_data.get("videos"):
                self.logger.info(f"Downloading {len(product_data['videos'])} videos")
                video_paths = await self._download_files(
                    [v["url"] for v in product_data["videos"] if isinstance(v, dict) and "url" in v],
                    "videos"
                )
                media_files["videos"] = video_paths

            self.logger.info(f"Media download completed: {media_files}")
            return media_files
        except Exception as e:
            self.logger.error(f"Error downloading media: {str(e)}")
            raise Exception(f"Error downloading media: {str(e)}")

    async def _download_files(self, urls: List[str], media_type: str) -> List[str]:
        """Download files from URLs and save them to the temp directory."""
        try:
            media_dir = self.temp_dir / media_type
            media_dir.mkdir(exist_ok=True)
            
            downloaded_files = []
            async with aiohttp.ClientSession() as session:
                for i, url in enumerate(urls):
                    try:
                        if not url:
                            continue
                            
                        # Create a unique filename
                        ext = os.path.splitext(url)[1] or ('.mp4' if media_type == 'videos' else '.jpg')
                        filename = f"{media_type}_{i}{ext}"
                        filepath = media_dir / filename
                        
                        # Download the file
                        async with session.get(url) as response:
                            if response.status == 200:
                                content = await response.read()
                                with open(filepath, 'wb') as f:
                                    f.write(content)
                                downloaded_files.append(str(filepath))
                                self.logger.info(f"Downloaded {media_type} file: {filename}")
                    except Exception as e:
                        self.logger.error(f"Error downloading {media_type} file {url}: {str(e)}")
                        continue
            
            return downloaded_files
        except Exception as e:
            self.logger.error(f"Error in _download_files: {str(e)}")
            return []

    def _create_text_clip(self, text: str, duration: float = 5.0) -> TextClip:
        """Create a text clip with fallback options."""
        try:
            if not self.use_simple_text:
                # Try with ImageMagick first
                return TextClip(
                    text,
                    fontsize=70,
                    color='white',
                    font='Arial-Bold',
                    size=(1920, 200),
                    method='caption'
                ).set_duration(duration)
        except Exception as e:
            self.logger.warning(f"Failed to create text clip with ImageMagick: {str(e)}")
            self.use_simple_text = True  # Switch to simple text rendering
        
        # Use simple text rendering
        return TextClip(
            text,
            fontsize=70,
            color='white',
            size=(1920, 200),
            method='label'  # Use simpler label method
        ).set_duration(duration)

    async def _generate_basic_video(self, media_files: Dict[str, List[str]], output_path: str) -> str:
        """Generate a basic video using only images."""
        try:
            self.logger.info("Starting basic video generation")
            self.logger.info(f"Media files: {media_files}")
            
            if not media_files['images']:
                self.logger.error("No images available for basic video generation")
                raise ValueError("No images available for basic video generation")
            
            self.logger.info(f"Creating basic video with {len(media_files['images'])} images")
            
            # Create clips for each image
            clips = []
            for i, image_path in enumerate(media_files['images']):
                try:
                    if not os.path.exists(image_path):
                        self.logger.warning(f"Image {i} not found at {image_path}, skipping")
                        continue
                        
                    self.logger.info(f"Creating clip for image {i}: {image_path}")
                    
                    # Load and resize image
                    img = Image.open(image_path)
                    # Resize to 1920x1080 while maintaining aspect ratio
                    img.thumbnail((1920, 1080), Image.Resampling.LANCZOS)
                    # Create a black background
                    background = Image.new('RGB', (1920, 1080), (0, 0, 0))
                    # Calculate position to center the image
                    x = (1920 - img.width) // 2
                    y = (1080 - img.height) // 2
                    # Paste the image onto the background
                    background.paste(img, (x, y))
                    # Save the processed image
                    processed_path = os.path.join(self.temp_dir, f"processed_image_{i}.jpg")
                    background.save(processed_path)
                    
                    # Create clip from processed image
                    clip = ImageClip(processed_path).set_duration(5)  # 5 seconds per image
                    clips.append(clip)
                    self.logger.info(f"Successfully created clip for image {i}")
                except Exception as e:
                    self.logger.error(f"Error creating clip for image {i}: {str(e)}")
                    continue
            
            if not clips:
                self.logger.error("No valid clips were created")
                raise ValueError("No valid clips were created")
            
            # Concatenate clips
            self.logger.info("Concatenating clips")
            final_clip = concatenate_videoclips(clips)
            
            # Write the video
            self.logger.info(f"Writing video to {output_path}")
            final_clip.write_videofile(
                output_path,
                fps=24,
                codec='libx264',
                audio_codec='aac',
                temp_audiofile=os.path.join(self.temp_dir, 'temp-audio.m4a'),
                remove_temp=True,
                threads=4,
                preset='ultrafast'  # Faster encoding
            )
            
            self.logger.info("Basic video generation completed successfully")
            return output_path
            
        except Exception as e:
            self.logger.error(f"Error in basic video generation: {str(e)}")
            raise Exception(f"Error generating basic video: {str(e)}")
        finally:
            # Clean up clips
            for clip in clips:
                try:
                    clip.close()
                except:
                    pass

    async def generate_video(self, script: Dict, product_data: Dict) -> str:
        """Generate a video from the script and product data."""
        try:
            self.logger.info("Starting video generation")
            self.logger.info(f"Script: {script}")
            self.logger.info(f"Product data: {product_data}")
            
            # Generate output path first
            output_path = os.path.join(self.output_dir, f"video_{uuid.uuid4()}.mp4")
            self.logger.info(f"Output path: {output_path}")
            
            media_files = await self._download_media(product_data)
            if not media_files or not media_files.get('images'):
                raise ValueError("No media files downloaded")
            
            self.logger.info(f"Downloaded media files: {media_files}")
            
            try:
                # Try to generate the full video first
                # Parse the script
                scenes = self._parse_script(script["content"])
                if not scenes:
                    raise ValueError("No scenes found in script")
                
                self.logger.info(f"Parsed scenes: {scenes}")
                
                # Create clips for each scene
                clips = []
                for i, scene in enumerate(scenes):
                    try:
                        self.logger.info(f"Creating clip for scene {i}: {scene}")
                        
                        # Create base clip (image or color)
                        try:
                            images = media_files.get('images', [])
                            if not images:
                                self.logger.warning(f"No images available, using color clip for scene {i}")
                                base_clip = ColorClip(size=(1920, 1080), color=(0, 0, 0))
                            else:
                                image_path = images[i % len(images)]
                                if not image_path or not os.path.exists(image_path):
                                    self.logger.warning(f"Invalid image path for scene {i}, using color clip")
                                    base_clip = ColorClip(size=(1920, 1080), color=(0, 0, 0))
                                else:
                                    self.logger.info(f"Using image {image_path} for scene {i}")
                                    base_clip = ImageClip(image_path)
                            
                            # Set duration for base clip
                            base_clip = base_clip.set_duration(5)
                            self.logger.info(f"Created base clip for scene {i}")
                        except Exception as e:
                            self.logger.error(f"Error creating base clip for scene {i}: {str(e)}")
                            base_clip = ColorClip(size=(1920, 1080), color=(0, 0, 0)).set_duration(5)
                        
                        # Create text clip
                        try:
                            text_clip = self._create_text_clip(scene['description'])
                            text_clip = text_clip.set_position(('center', 'bottom'))
                            self.logger.info(f"Created text clip for scene {i}")
                        except Exception as e:
                            self.logger.error(f"Error creating text clip for scene {i}: {str(e)}")
                            # Create a simple text clip as fallback
                            text_clip = TextClip(
                                scene['description'],
                                fontsize=70,
                                color='white',
                                size=(1920, 200),
                                method='label'
                            ).set_duration(5).set_position(('center', 'bottom'))
                        
                        # Composite the clips
                        try:
                            final_clip = CompositeVideoClip([base_clip, text_clip])
                            clips.append(final_clip)
                            self.logger.info(f"Successfully created final clip for scene {i}")
                        except Exception as e:
                            self.logger.error(f"Error compositing clips for scene {i}: {str(e)}")
                            # Try a simpler composition as fallback
                            try:
                                final_clip = CompositeVideoClip([
                                    ColorClip(size=(1920, 1080), color=(0, 0, 0)).set_duration(5),
                                    text_clip
                                ])
                                clips.append(final_clip)
                                self.logger.info(f"Created fallback final clip for scene {i}")
                            except Exception as fallback_error:
                                self.logger.error(f"Error creating fallback final clip for scene {i}: {str(fallback_error)}")
                                continue
                        
                    except Exception as e:
                        self.logger.error(f"Error in scene {i} processing: {str(e)}")
                        continue
                
                if not clips:
                    raise ValueError("No valid clips were created")
                
                self.logger.info(f"Created {len(clips)} clips")
                
                # Concatenate all clips
                final_video = concatenate_videoclips(clips)
                
                # Add background music if available
                if media_files.get('audio') and os.path.exists(media_files['audio']):
                    try:
                        audio = AudioFileClip(media_files['audio'])
                        # Loop audio if needed
                        if audio.duration < final_video.duration:
                            audio = audio.loop(duration=final_video.duration)
                        final_video = final_video.set_audio(audio)
                        self.logger.info("Successfully added audio")
                    except Exception as e:
                        self.logger.error(f"Error adding audio: {str(e)}")
                
                # Write the result
                self.logger.info(f"Writing final video to {output_path}")
                final_video.write_videofile(
                    output_path,
                    fps=24,
                    codec='libx264',
                    audio_codec='aac',
                    temp_audiofile='temp-audio.m4a',
                    remove_temp=True
                )
                
                # Clean up
                self.logger.info("Cleaning up temporary files")
                for clip in clips:
                    clip.close()
                final_video.close()
                
                # Clean up downloaded media
                await self._cleanup_media(media_files)
                
                self.logger.info("Video generation completed successfully")
                return output_path
                
            except Exception as e:
                self.logger.error(f"Error in full video generation: {str(e)}")
                self.logger.info("Falling back to basic video generation")
                
                # Try basic video generation as fallback
                try:
                    basic_video_path = await self._generate_basic_video(media_files, output_path)
                    self.logger.info("Successfully generated basic video")
                    return basic_video_path
                except Exception as basic_error:
                    self.logger.error(f"Error in basic video generation: {str(basic_error)}")
                    raise Exception(f"Both full and basic video generation failed: {str(e)} -> {str(basic_error)}")
                    
        except Exception as e:
            self.logger.error(f"Error generating video: {str(e)}")
            # Clean up any downloaded files
            if 'media_files' in locals():
                await self._cleanup_media(media_files)
            raise Exception(f"Error generating video: {str(e)}")

    def _parse_script(self, script: str) -> List[Dict]:
        """Parse the script into scenes with timestamps."""
        try:
            self.logger.info("Starting script parsing")
            scenes = []
            
            # Split script into sections (header and scenes)
            sections = script.split('---')
            if len(sections) < 2:
                raise Exception("Script must contain a header and scenes section separated by '---'")
            
            # Get the scenes section
            scenes_section = sections[1].strip()
            self.logger.info(f"Scenes section: {scenes_section}")
            
            # Split into lines and process each line
            lines = [line.strip() for line in scenes_section.split('\n') if line.strip()]
            
            for line in lines:
                if not line.startswith('[') or ']' not in line:
                    continue
                    
                try:
                    # Extract timestamp
                    time_str = line[1:line.index(']')]
                    minutes, seconds = map(int, time_str.split(':'))
                    timestamp = minutes * 60 + seconds
                    
                    # Extract description
                    description = line[line.index(']') + 1:].strip()
                    if description.startswith('*'):
                        description = description[1:-1]  # Remove asterisks
                    
                    # Calculate duration based on next timestamp or default
                    duration = 5  # Default duration
                    
                    # Add scene
                    scene = {
                        'timestamp': timestamp,
                        'description': description,
                        'duration': duration
                    }
                    scenes.append(scene)
                    self.logger.info(f"Added scene: {scene}")
                    
                except Exception as e:
                    self.logger.error(f"Error parsing line '{line}': {str(e)}")
                    continue
            
            # Calculate durations based on timestamps
            for i in range(len(scenes) - 1):
                scenes[i]['duration'] = scenes[i + 1]['timestamp'] - scenes[i]['timestamp']
            
            # Set duration for last scene
            if scenes:
                scenes[-1]['duration'] = 5  # Default duration for last scene
            
            if not scenes:
                self.logger.error("No valid scenes found in script")
                self.logger.debug(f"Script content: {script}")
                raise Exception("No valid scenes found in script")
            
            self.logger.info(f"Successfully parsed {len(scenes)} scenes: {scenes}")
            return scenes
            
        except Exception as e:
            self.logger.error(f"Error parsing script: {str(e)}")
            raise Exception(f"Error parsing script: {str(e)}")

    async def _create_scene_clip(self, scene: Dict, media_files: Dict[str, List[str]]) -> Optional[VideoFileClip]:
        """Create a video clip for a scene."""
        try:
            duration = scene.get('duration', 5)
            self.logger.info(f"Creating scene clip: {scene['description']} with duration {duration}s")
            
            # Try to use an image for the scene
            if media_files.get("images"):
                # Use different images for different scenes
                image_index = scene.get('timestamp', 0) % len(media_files["images"])
                image_path = media_files["images"][image_index]
                self.logger.info(f"Using image {image_index} for scene: {scene['description']}")
                
                # Create image clip
                clip = ImageClip(image_path, duration=duration)
                # Resize to 1920x1080 while maintaining aspect ratio
                clip = clip.resize(width=1920)
            else:
                # Create a color background if no images are available
                self.logger.warning("No images available, using color background")
                clip = ColorClip(size=(1920, 1080), color=(0, 0, 0), duration=duration)
            
            # Add text overlay
            text_clip = TextClip(
                scene["description"],
                fontsize=40,
                color='white',
                bg_color='rgba(0,0,0,0.5)',
                size=(1920, None),
                method='caption',
                align='center'
            ).set_duration(duration)
            
            # Position text in the center
            text_clip = text_clip.set_position(('center', 'center'))
            
            # Combine video and text
            final_clip = CompositeVideoClip([clip, text_clip])
            self.logger.info(f"Created scene clip for: {scene['description']}")
            return final_clip
            
        except Exception as e:
            self.logger.error(f"Error creating scene clip: {str(e)}")
            return None

    async def _download_media(self, product_data: Dict) -> Dict[str, List[str]]:
        """Download media files from product data."""
        try:
            self.logger.info("Starting media download")
            self.logger.info(f"Product data: {product_data}")
            
            media_files = {
                'images': [],
                'audio': None
            }
            
            # Download images
            if 'images' in product_data and product_data['images']:
                self.logger.info(f"Found {len(product_data['images'])} images to download")
                for i, image_url in enumerate(product_data['images']):
                    try:
                        if not image_url:
                            self.logger.warning(f"Empty image URL at index {i}, skipping")
                            continue
                            
                        self.logger.info(f"Downloading image {i}: {image_url}")
                        image_path = os.path.join(self.temp_dir, f"image_{i}.jpg")
                        
                        # Use requests with proper headers
                        import requests
                        headers = {
                            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                            'Accept': '*/*'
                        }
                        response = requests.get(image_url, stream=True, timeout=10, headers=headers)
                        
                        if response.status_code == 200:
                            # Save the image
                            with open(image_path, 'wb') as f:
                                for chunk in response.iter_content(chunk_size=8192):
                                    if chunk:
                                        f.write(chunk)
                            
                            # Validate saved image
                            if os.path.exists(image_path):
                                file_size = os.path.getsize(image_path)
                                self.logger.info(f"Image {i} saved. File size: {file_size} bytes")
                                media_files['images'].append(image_path)
                            else:
                                self.logger.warning(f"Failed to save image {i}, file not created")
                        else:
                            self.logger.warning(f"Failed to download image {i}, status: {response.status_code}")
                    except Exception as e:
                        self.logger.error(f"Error downloading image {i}: {str(e)}")
                        continue
            else:
                self.logger.warning("No images found in product data")
            
            # If no images were downloaded, create a black screen
            if not media_files['images']:
                self.logger.warning("No images downloaded, creating a black screen")
                from moviepy.editor import ColorClip
                color_clip = ColorClip(size=(1920, 1080), color=(0, 0, 0))
                color_path = os.path.join(self.temp_dir, "color_clip.jpg")
                color_clip.save_frame(color_path, t=0)
                media_files['images'].append(color_path)
                self.logger.info("Created black screen as fallback")
            
            return media_files
            
        except Exception as e:
            self.logger.error(f"Error in media download: {str(e)}")
            raise Exception(f"Error downloading media: {str(e)}")

    async def _cleanup_media(self, media_files: Dict[str, List[str]]) -> None:
        """Clean up downloaded media files."""
        try:
            self.logger.info("Cleaning up media files")
            for image_path in media_files.get('images', []):
                try:
                    if os.path.exists(image_path):
                        os.remove(image_path)
                except Exception as e:
                    self.logger.error(f"Error removing image {image_path}: {str(e)}")
            
            if media_files.get('audio'):
                try:
                    if os.path.exists(media_files['audio']):
                        os.remove(media_files['audio'])
                except Exception as e:
                    self.logger.error(f"Error removing audio file: {str(e)}")
            
            self.logger.info("Media cleanup completed")
        except Exception as e:
            self.logger.error(f"Error in media cleanup: {str(e)}")

    def _create_video_clip(self, media_files: Dict[str, List[str]], script: List[Dict]) -> str:
        """Create video clip from media files and script."""
        try:
            self.logger.info("Starting video creation")
            from moviepy.editor import ImageClip, TextClip, CompositeVideoClip, concatenate_videoclips
            
            clips = []
            scene_duration = 30  # Fixed duration for each scene
            
            # Process each scene
            for i, scene in enumerate(script):
                try:
                    # Get corresponding image
                    if i < len(media_files['images']):
                        image_path = media_files['images'][i]
                        self.logger.info(f"Processing image {i}: {image_path}")
                        
                        # Create image clip
                        image_clip = ImageClip(image_path)
                        image_clip = image_clip.set_duration(scene_duration)
                        
                        # Add text if present
                        if 'text' in scene and scene['text']:
                            text_clip = TextClip(
                                scene['text'],
                                fontsize=70,
                                color='white',
                                font='Arial'
                            )
                            text_clip = text_clip.set_duration(scene_duration)
                            text_clip = text_clip.set_position('center')
                            
                            # Combine image and text
                            scene_clip = CompositeVideoClip([image_clip, text_clip])
                        else:
                            scene_clip = image_clip
                        
                        clips.append(scene_clip)
                        self.logger.info(f"Added scene {i}")
                    else:
                        self.logger.warning(f"No image available for scene {i}")
                
                except Exception as scene_err:
                    self.logger.error(f"Error processing scene {i}: {str(scene_err)}")
                    continue
            
            if not clips:
                raise ValueError("No valid clips were created")
            
            # Concatenate all clips
            final_clip = concatenate_videoclips(clips)
            
            # Save the final video
            output_path = os.path.join(self.output_dir, "output.mp4")
            final_clip.write_videofile(
                output_path,
                fps=30,
                codec='libx264',
                audio=False,
                preset='medium',
                threads=2
            )
            
            self.logger.info(f"Video saved to {output_path}")
            
            # Clean up clips
            for clip in clips:
                clip.close()
            final_clip.close()
            
            return output_path
            
        except Exception as e:
            self.logger.error(f"Error in video creation: {str(e)}")
            raise Exception(f"Error creating video: {str(e)}") 
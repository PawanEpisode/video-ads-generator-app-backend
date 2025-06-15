from typing import Dict, List, Optional
import os
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import uuid
import aiohttp
import asyncio
from pathlib import Path
import logging
import tempfile
import shutil
import textwrap
import subprocess
from gtts import gTTS
from pydub import AudioSegment

logger = logging.getLogger(__name__)

class VideoGenerator:
    """Service for generating videos from product data."""
    
    def __init__(self):
        """Initialize the video generator."""
        self.logger = logging.getLogger(__name__)
        
        # Create temporary directory
        self.temp_dir = os.path.join(os.getcwd(), "temp")
        os.makedirs(self.temp_dir, exist_ok=True)
        
        # Create output directory
        self.output_dir = os.path.join(os.getcwd(), "output")
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Video settings
        self.fps = 24  # Frames per second
        self.duration_per_image = 5  # Duration in seconds for each image
        self.text_color = (255, 255, 255)  # White color for text
        self.text_scale = 0.8  # Reduced text scale
        self.text_thickness = 1  # Reduced thickness
        self.text_padding = 20  # Reduced padding
        
        # Font settings
        self.font = cv2.FONT_HERSHEY_SIMPLEX
        self.font_scale = 0.8  # Reduced font scale
        self.font_thickness = 1  # Reduced font thickness
        
        # Audio settings
        self.audio_fade_duration = 500  # milliseconds
        self.audio_padding = 0.5  # seconds
        
        self.logger.info("VideoGenerator initialized")
        
        # Set up directories
        self.base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        
        # Clean up any existing files in temp directory
        self._cleanup_temp_files()
        
        # Check for ffmpeg
        try:
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

    def _create_text_overlay(self, image: np.ndarray, text: str) -> np.ndarray:
        """Create text overlay on image with text wrapping."""
        try:
            # Create a copy of the image
            result = image.copy()
            
            # Get image dimensions
            height, width = image.shape[:2]
            
            # Wrap text to fit width
            max_width = width - (2 * self.text_padding)  # Leave padding on both sides
            words = text.split()
            lines = []
            current_line = []
            
            for word in words:
                # Test if adding this word exceeds max width
                test_line = ' '.join(current_line + [word])
                (text_width, _), _ = cv2.getTextSize(
                    test_line, self.font, self.font_scale, self.font_thickness
                )
                
                if text_width <= max_width:
                    current_line.append(word)
                else:
                    if current_line:
                        lines.append(' '.join(current_line))
                    current_line = [word]
            
            if current_line:
                lines.append(' '.join(current_line))
            
            # Calculate total text height and line height
            line_height = int(self.font_scale * 30)  # Approximate line height
            total_text_height = len(lines) * line_height
            
            # Calculate background rectangle dimensions
            max_line_width = 0
            for line in lines:
                (line_width, _), _ = cv2.getTextSize(
                    line, self.font, self.font_scale, self.font_thickness
                )
                max_line_width = max(max_line_width, line_width)
            
            # Calculate background position (centered horizontally, at bottom)
            bg_width = max_line_width + (2 * self.text_padding)
            bg_height = total_text_height + (2 * self.text_padding)
            bg_x1 = (width - bg_width) // 2
            bg_y1 = height - bg_height - self.text_padding  # Position at bottom with padding
            bg_x2 = bg_x1 + bg_width
            bg_y2 = bg_y1 + bg_height
            
            # Create semi-transparent background for text
            overlay = result.copy()
            
            # Draw background
            cv2.rectangle(
                overlay,
                (bg_x1, bg_y1),
                (bg_x2, bg_y2),
                (0, 0, 0),
                -1
            )
            
            # Calculate starting y position for text (centered in background)
            text_start_y = bg_y1 + self.text_padding + line_height
            
            # Add text lines
            for i, line in enumerate(lines):
                (line_width, _), _ = cv2.getTextSize(
                    line, self.font, self.font_scale, self.font_thickness
                )
                text_x = (width - line_width) // 2
                current_y = text_start_y + (i * line_height)
                
                cv2.putText(
                    overlay,
                    line,
                    (text_x, current_y),
                    self.font,
                    self.font_scale,
                    self.text_color,
                    self.font_thickness,
                    cv2.LINE_AA
                )
            
            # Blend overlay with original image
            alpha = 0.7  # Transparency factor
            cv2.addWeighted(overlay, alpha, result, 1 - alpha, 0, result)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error creating text overlay: {str(e)}")
            return image

    def _resize_image(self, image: np.ndarray, target_size: tuple = (1920, 1080)) -> np.ndarray:
        """Resize image while maintaining aspect ratio."""
        try:
            h, w = image.shape[:2]
            target_w, target_h = target_size
            
            # Calculate aspect ratios
            aspect_ratio = w / h
            target_ratio = target_w / target_h
            
            if aspect_ratio > target_ratio:
                # Image is wider than target
                new_w = target_w
                new_h = int(target_w / aspect_ratio)
            else:
                # Image is taller than target
                new_h = target_h
                new_w = int(target_h * aspect_ratio)
            
            # Resize image
            resized = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_LANCZOS4)
            
            # Create black background
            background = np.zeros((target_h, target_w, 3), dtype=np.uint8)
            
            # Calculate position to center the image
            x = (target_w - new_w) // 2
            y = (target_h - new_h) // 2
            
            # Place resized image on background
            background[y:y+new_h, x:x+new_w] = resized
            
            return background
            
        except Exception as e:
            self.logger.error(f"Error resizing image: {str(e)}")
            return image

    async def _generate_basic_video(self, media_files: Dict[str, List[str]], output_path: str) -> str:
        """Generate a basic video using only images."""
        try:
            self.logger.info("Starting basic video generation")
            
            if not media_files['images']:
                self.logger.error("No images available for basic video generation")
                raise ValueError("No images available for basic video generation")
            
            # Video settings
            fps = 24
            frame_duration = 5  # seconds per image
            frame_size = (1920, 1080)
            
            # Create video writer with H.264 codec
            temp_output = output_path.replace('.mp4', '_temp.mp4')
            fourcc = cv2.VideoWriter_fourcc(*'avc1')  # Use H.264 codec
            out = cv2.VideoWriter(temp_output, fourcc, fps, frame_size)
            
            if not out.isOpened():
                raise Exception("Failed to create video writer")
            
            # Process each image
            for image_path in media_files['images']:
                try:
                    # Read image
                    image = cv2.imread(image_path)
                    if image is None:
                        self.logger.warning(f"Failed to read image: {image_path}")
                        continue
                    
                    # Resize image
                    image = self._resize_image(image, frame_size)
                    
                    # Write frames
                    for _ in range(fps * frame_duration):
                        out.write(image)
                    
                    self.logger.info(f"Processed image: {image_path}")
                    
                except Exception as e:
                    self.logger.error(f"Error processing image {image_path}: {str(e)}")
                    continue
            
            # Release video writer
            out.release()
            
            # Verify the temp file exists and has content
            if not os.path.exists(temp_output) or os.path.getsize(temp_output) == 0:
                raise Exception("Failed to create temporary video file")
            
            # Convert to final MP4 using ffmpeg
            try:
                ffmpeg_cmd = [
                    'ffmpeg',
                    '-y',  # Overwrite output file if it exists
                    '-i', temp_output,
                    '-c:v', 'libx264',
                    '-preset', 'medium',
                    '-crf', '23',
                    '-movflags', '+faststart',  # Enable fast start for web playback
                    output_path
                ]
                
                result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)
                if result.returncode != 0:
                    self.logger.error(f"FFmpeg error: {result.stderr}")
                    raise Exception(f"FFmpeg conversion failed: {result.stderr}")
                
                # Verify the output file exists and has content
                if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
                    raise Exception("Failed to create final video file")
                
            finally:
                # Clean up temporary file
                if os.path.exists(temp_output):
                    os.remove(temp_output)
            
            self.logger.info("Basic video generation completed successfully")
            return output_path
            
        except Exception as e:
            self.logger.error(f"Error in basic video generation: {str(e)}")
            raise Exception(f"Error generating basic video: {str(e)}")

    async def generate_video(self, script: Dict, product_data: Dict) -> str:
        """Generate a video from the script and product data."""
        try:
            self.logger.info("Starting video generation")
            
            # Download media files
            media_files = await self.download_media(product_data)
            
            if not media_files['images']:
                raise Exception("No images available for video generation")
            
            # Parse the script
            scenes = self._parse_script(script["content"])
            if not scenes:
                raise ValueError("No scenes found in script")
            
            # Create video
            output_path = os.path.join(self.output_dir, f"video_{uuid.uuid4()}.mp4")
            temp_output = os.path.join(self.temp_dir, "temp_output.mp4")
            temp_audio = os.path.join(self.temp_dir, "temp_audio.mp3")
            
            # Get dimensions from first image
            first_image = cv2.imread(media_files['images'][0])
            if first_image is None:
                raise Exception("Failed to read first image")
                
            height, width = first_image.shape[:2]
            
            # Create video writer
            fourcc = cv2.VideoWriter_fourcc(*'avc1')  # Use H.264 codec
            video_writer = cv2.VideoWriter(temp_output, fourcc, self.fps, (width, height))
            
            if not video_writer.isOpened():
                raise Exception("Failed to create video writer")

            # Generate voice overs for each scene
            audio_segments = []
            for scene in scenes:
                try:
                    # Generate voice over for the scene
                    audio_path = self._generate_voice_over(scene['description'])
                    if audio_path:
                        audio_segments.append(AudioSegment.from_mp3(audio_path))
                except Exception as e:
                    self.logger.warning(f"Failed to generate voice over for scene: {str(e)}")
            
            # Combine audio segments if we have any
            if audio_segments:
                final_audio = sum(audio_segments)
                final_audio.export(temp_audio, format="mp3")
                self.logger.info("Voice over audio generated successfully")
            
            # Process each scene
            for scene in scenes:
                try:
                    # Get image for scene
                    image_index = scene.get('timestamp', 0) % len(media_files['images'])
                    image_path = media_files['images'][image_index]
                    
                    # Read image
                    image = cv2.imread(image_path)
                    if image is None:
                        self.logger.warning(f"Failed to read image: {image_path}")
                        continue
                        
                    # Resize image if needed
                    if image.shape[:2] != (height, width):
                        image = cv2.resize(image, (width, height))
                    
                    # Add text overlay
                    image = self._create_text_overlay(image, scene['description'])
                    
                    # Calculate number of frames for this scene
                    num_frames = int(scene.get('duration', 5) * self.fps)
                    
                    # Write frames
                    for _ in range(num_frames):
                        video_writer.write(image)
                        
                    self.logger.info(f"Processed scene: {scene['description']}")
                        
                except Exception as e:
                    self.logger.error(f"Error processing scene: {str(e)}")
                    continue
            
            # Release video writer
            video_writer.release()
            
            # Combine video and audio if we have audio
            if os.path.exists(temp_audio):
                try:
                    ffmpeg_cmd = [
                        'ffmpeg', '-y',
                        '-i', temp_output,
                        '-i', temp_audio,
                        '-c:v', 'copy',
                        '-c:a', 'aac',
                        '-b:a', '192k',
                        '-ar', '44100',
                        '-ac', '2',
                        '-shortest',
                        '-movflags', '+faststart',
                        output_path
                    ]
                    
                    process = await asyncio.create_subprocess_exec(
                        *ffmpeg_cmd,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    
                    stdout, stderr = await process.communicate()
                    
                    if process.returncode != 0:
                        self.logger.error(f"FFmpeg error: {stderr.decode()}")
                        raise Exception(f"FFmpeg conversion failed: {stderr.decode()}")
                except Exception as e:
                    self.logger.error(f"Error combining video and audio: {str(e)}")
                    # If audio combination fails, just use the video
                    os.rename(temp_output, output_path)
            else:
                # If no audio, just use the video
                os.rename(temp_output, output_path)
            
            # Verify the output file
            if not os.path.exists(output_path):
                raise Exception("Video generation failed: Output file not created")
                
            file_size = os.path.getsize(output_path)
            if file_size == 0:
                raise Exception("Video generation failed: Output file is empty")
                
            self.logger.info(f"Video generated successfully. File size: {file_size} bytes")
            return output_path
                
        except Exception as e:
            self.logger.error(f"Error in video generation: {str(e)}")
            raise Exception(f"Error generating video: {str(e)}")
        finally:
            # Cleanup temporary files
            try:
                for temp_file in [temp_output, temp_audio]:
                    if os.path.exists(temp_file):
                        os.remove(temp_file)
            except Exception as e:
                self.logger.warning(f"Error cleaning up temporary files: {str(e)}")

    def _parse_script(self, script: str) -> List[Dict]:
        """Parse the script into scenes."""
        try:
            scenes = []
            lines = script.strip().split('\n')
            
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
                raise Exception("No valid scenes found in script")
            
            return scenes
            
        except Exception as e:
            self.logger.error(f"Error parsing script: {str(e)}")
            raise Exception(f"Error parsing script: {str(e)}")

    async def download_media(self, product_data: Dict) -> Dict[str, List[str]]:
        """Download media files from product data."""
        try:
            self.logger.warning("Starting media download", product_data)
            
            media_files = {
                'images': [],
                'audio': None
            }
            
            # Download images
            if 'images' in product_data and product_data['images']:
                self.logger.warning(f"Found {len(product_data['images'])} images to download")
                
                # Headers to avoid CORS and mimic browser request
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                    'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Referer': 'https://www.google.com/',
                    'sec-ch-ua': '"Google Chrome";v="91", "Chromium";v="91"',
                    'sec-ch-ua-mobile': '?0',
                    'sec-fetch-dest': 'image',
                    'sec-fetch-mode': 'no-cors',
                    'sec-fetch-site': 'cross-site'
                }
                
                # Create a session for all downloads
                async with aiohttp.ClientSession() as session:
                    for i, image_url in enumerate(product_data['images']):
                        try:
                            if not image_url or not isinstance(image_url, str):
                                self.logger.warning(f"Invalid image URL at index {i}, skipping")
                                continue
                                
                            self.logger.warning(f"Downloading image {i}: {image_url}")
                            # Check if this is a local file path
                            if image_url.startswith('/') or image_url.startswith('./'):
                                # If it's a local file, just add it to media_files
                                if os.path.exists(image_url):
                                    self.logger.warning(f"Using existing local file: {image_url}")
                                    media_files['images'].append(image_url)
                                else:
                                    self.logger.warning(f"Local file not found: {image_url}")
                                continue
                            # Download the image
                            async with session.get(image_url, headers=headers, timeout=30) as response:
                                if response.status == 200:
                                    # Read image data
                                    image_data = await response.read()
                                    
                                    # Convert to numpy array
                                    image_array = np.asarray(bytearray(image_data), dtype=np.uint8)
                                    image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
                                    
                                    if image is not None:
                                        # Save the image
                                        image_path = os.path.join(self.temp_dir, f"image_{i}.jpg")
                                        self.logger.warning(f"Saving image to: {image_path}")
                                        success = cv2.imwrite(image_path, image)
                                        
                                        if success:
                                            # Verify the saved image
                                            if os.path.exists(image_path):
                                                file_size = os.path.getsize(image_path)
                                                self.logger.warning(f"Image {i} saved successfully. File size: {file_size} bytes")
                                                # Add the local file path to media_files
                                                media_files['images'].append(image_path)
                                            else:
                                                self.logger.warning(f"Failed to save image {i}, file not created")
                                        else:
                                            self.logger.warning(f"Failed to save image {i}, cv2.imwrite returned False")
                                    else:
                                        self.logger.warning(f"Failed to decode image {i} from URL: {image_url}")
                                else:
                                    self.logger.warning(f"Failed to download image {i}, status: {response.status}")
                                    
                        except aiohttp.ClientError as e:
                            self.logger.error(f"Network error downloading image {i} from {image_url}: {str(e)}")
                            continue
                        except Exception as e:
                            self.logger.error(f"Error downloading image {i} from {image_url}: {str(e)}")
                            continue
            else:
                self.logger.warning("No images found in product data")
            
            # If no images were downloaded, create a black screen
            if not media_files['images']:
                self.logger.warning("No images downloaded, creating a black screen")
                black_screen = np.zeros((1080, 1920, 3), dtype=np.uint8)
                black_screen_path = os.path.join(self.temp_dir, "black_screen.jpg")
                cv2.imwrite(black_screen_path, black_screen)
                media_files['images'].append(black_screen_path)
                self.logger.info("Created black screen as fallback")
            
            self.logger.warning(f"Downloaded {len(media_files['images'])} images successfully")
            return media_files
            
        except Exception as e:
            self.logger.error(f"Error in media download: {str(e)}")
            raise Exception(f"Error downloading media: {str(e)}")

    def _generate_voice_over(self, text: str) -> Optional[str]:
        """Generate voice over for text using gTTS"""
        try:
            if not text:
                return None
                
            # Create output directory if it doesn't exist
            os.makedirs(self.temp_dir, exist_ok=True)
            
            # Generate unique filename
            output_path = os.path.join(self.temp_dir, f"voice_over_{uuid.uuid4()}.mp3")
            
            # Generate speech with faster rate
            tts = gTTS(text=text, lang='en', slow=False)
            tts.save(output_path)
            
            self.logger.info(f"Generated voice over for text: {text[:50]}...")
            return output_path
            
        except Exception as e:
            self.logger.error(f"Error generating voice over: {str(e)}")
            return None

    def cleanup(self):
        """Clean up temporary files"""
        try:
            for file in os.listdir(self.temp_dir):
                file_path = os.path.join(self.temp_dir, file)
                if os.path.isfile(file_path):
                    os.remove(file_path)
        except Exception as e:
            logging.error(f"Error cleaning up temporary files: {str(e)}") 
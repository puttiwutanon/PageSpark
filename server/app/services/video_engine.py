"""
server/app/services/video_engine.py

Video editing pipeline that combines Manim rendered video with TTS audio
to produce the final short-form video with synchronized voiceover.
"""
import os
import logging
from typing import Optional

import moviepy.editor as mp

logger = logging.getLogger(__name__)


class VideoEngine:
    """Combine Manim video with TTS audio into final rendered video."""
    
    def __init__(self, output_dir: str = "renders/final"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        logger.info(f"🎬 VideoEngine initialized with output_dir: {output_dir}")
    
    def combine_video_audio(
        self,
        video_path: str,
        audio_path: str,
        episode_number: int,
        output_filename: Optional[str] = None,
    ) -> Optional[str]:
        """
        Combine a Manim video with TTS audio into a final video.
        
        Args:
            video_path: Path to the Manim rendered video (MP4)
            audio_path: Path to the TTS audio (MP3)
            episode_number: Episode number for naming
            output_filename: Optional custom filename
        
        Returns:
            Path to the final combined video, or None if failed
        """
        if not os.path.exists(video_path):
            logger.error(f"❌ Video file not found: {video_path}")
            return None
        
        if not os.path.exists(audio_path):
            logger.error(f"❌ Audio file not found: {audio_path}")
            return None
        
        try:
            # Determine output path
            if output_filename is None:
                output_filename = f"episode_{episode_number}_final.mp4"
            output_path = os.path.join(self.output_dir, output_filename)
            
            logger.info(f"🎬 Combining video and audio...")
            logger.info(f"   Video: {video_path}")
            logger.info(f"   Audio: {audio_path}")
            logger.info(f"   Output: {output_path}")
            
            # Load video and audio
            video_clip = mp.VideoFileClip(video_path)
            audio_clip = mp.AudioFileClip(audio_path)
            
            # Get durations
            video_duration = video_clip.duration
            audio_duration = audio_clip.duration
            
            logger.info(f"   Video duration: {video_duration:.1f}s")
            logger.info(f"   Audio duration: {audio_duration:.1f}s")
            
            # If audio is longer than video, freeze last frame to extend
            if audio_duration > video_duration:
                logger.info(f"   Audio longer than video, extending video...")
                # Get the last frame as an image
                last_frame = video_clip.get_frame(video_duration - 0.1)
                freeze_clip = mp.ImageClip(last_frame, duration=audio_duration - video_duration)
                video_clip = mp.concatenate_videoclips([video_clip, freeze_clip])
                logger.info(f"   Extended video to {audio_duration:.1f}s")
            
            # If video is longer than audio, trim video
            if video_duration > audio_duration:
                logger.info(f"   Video longer than audio, trimming video...")
                video_clip = video_clip.subclip(0, audio_duration)
                logger.info(f"   Trimmed video to {audio_duration:.1f}s")
            
            # Set audio to video
            final_clip = video_clip.set_audio(audio_clip)
            
            # Write final video
            logger.info(f"   Rendering final video...")
            final_clip.write_videofile(
                output_path,
                fps=30,
                codec='libx264',
                audio_codec='aac',
                threads=4,
                verbose=False,
                logger=None,
            )
            
            # Clean up
            video_clip.close()
            audio_clip.close()
            final_clip.close()
            
            logger.info(f"✅ Final video created: {output_path}")
            logger.info(f"   Size: {os.path.getsize(output_path) / (1024*1024):.2f} MB")
            
            return output_path
            
        except Exception as e:
            logger.error(f"❌ Error combining video and audio: {e}", exc_info=True)
            return None
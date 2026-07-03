"""
Upload a rendered Manim .mp4 to Firebase Storage and record it in
the top-level `videos` Firestore collection, keyed by uid.
"""

import os
import glob
import logging
from app.storage.firebase_client import db, bucket
from firebase_admin import firestore

# Enhanced logging configuration
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def find_rendered_mp4(output_dir, scene_filename_stem=None):
    """
    Manim's --media_dir output nests files under
    <output_dir>/videos/<scene_filename>/<quality>/<SceneClassName>.mp4
    so we glob for it rather than hardcoding the path -- the quality
    folder name changes depending on -pql vs -qh.
    """
    pattern = os.path.join(output_dir, "videos", "**", "PhysicsScene.mp4")
    logger.debug(f"🔍 Looking for MP4 with pattern: {pattern}")
    matches = glob.glob(pattern, recursive=True)
    
    if matches:
        logger.info(f"✅ Found MP4 file: {matches[0]}")
        return matches[0]
    else:
        logger.warning(f"❌ No MP4 file found matching pattern: {pattern}")
        return None


def upload_manim_render(uid, episode_number, output_dir="renders"):
    """Legacy function - kept for backward compatibility."""
    logger.info(f"📤 upload_manim_render called for uid={uid}, episode={episode_number}")
    return upload_episode_video(
        video_path=None,  # Will auto-find
        uid=uid,
        episode_number=episode_number,
        lesson_id=None,
        question_title=None,
        output_dir=output_dir,
    )


def upload_episode_video(video_path, uid, episode_number, lesson_id=None, question_title=None, output_dir="renders"):
    """
    Upload a rendered Manim .mp4 to Firebase Storage and record it in Firestore.
    
    Args:
        video_path: Path to the rendered video file. If None, auto-find it.
        uid: User ID for the upload.
        episode_number: Episode number for this video.
        lesson_id: Optional lesson ID for grouping.
        question_title: Optional question title for metadata.
        output_dir: Directory where renders are stored.
    
    Returns:
        dict: Document data with video_url and doc_id, or None if upload failed.
    """
    logger.info(f"📤 ===== STARTING UPLOAD for episode {episode_number} =====")
    logger.info(f"   uid={uid}, lesson_id={lesson_id}")
    logger.info(f"   video_path={video_path}")
    
    try:
        # If video_path is None or doesn't exist, try to find it
        if video_path is None or not os.path.exists(video_path):
            logger.info(f"🔍 Video path not provided or not found, searching in {output_dir}...")
            local_path = find_rendered_mp4(output_dir, f"scene_ep_{episode_number}")
            if not local_path:
                logger.error(f"❌ No rendered file found for episode {episode_number}")
                return None
            video_path = local_path
            logger.info(f"✅ Found video file: {video_path}")
        
        if not os.path.exists(video_path):
            logger.error(f"❌ Video file not found: {video_path}")
            return None

        # Get file size for logging
        file_size = os.path.getsize(video_path) / (1024 * 1024)  # MB
        logger.info(f"📹 Video file size: {file_size:.2f} MB")

        # Create the Firestore doc first so we have an ID to name the Storage path with
        logger.info(f"📝 Creating Firestore document in 'videos' collection...")
        video_doc_ref = db.collection("videos").document()
        video_id = video_doc_ref.id
        logger.info(f"📄 Document ID: {video_id}")

        blob_path = f"videos/{uid}/{video_id}.mp4"
        logger.info(f"📤 Uploading to Storage path: {blob_path}")
        blob = bucket.blob(blob_path)
        
        # Upload the video
        logger.info(f"⏳ Uploading video file...")
        blob.upload_from_filename(video_path)
        logger.info(f"✅ Video uploaded successfully!")
        
        # Make public
        logger.info(f"🔓 Making video public...")
        blob.make_public()
        logger.info(f"✅ Video is now public")

        # Build document data
        doc_data = {
            "uid": uid,
            "episodeNumber": episode_number,
            "status": "manim_done",
            "manimVideoUrl": blob.public_url,
            "createdAt": firestore.SERVER_TIMESTAMP,
            "videoId": video_id,
        }
        
        if lesson_id:
            doc_data["lessonId"] = lesson_id
            logger.info(f"   lessonId: {lesson_id}")
        
        if question_title:
            doc_data["questionTitle"] = question_title
            logger.info(f"   questionTitle: {question_title}")

        logger.info(f"📝 Saving to Firestore with data: {doc_data}")
        video_doc_ref.set(doc_data)

        logger.info(f"✅ ===== UPLOAD COMPLETE for episode {episode_number} =====")
        logger.info(f"   Document ID: {video_id}")
        logger.info(f"   Video URL: {blob.public_url}")
        
        return {
            "doc_id": video_id,
            "video_url": blob.public_url,
            **doc_data
        }

    except Exception as e:
        logger.error(f"❌ Error uploading episode video: {e}", exc_info=True)
        return None
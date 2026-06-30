"""
Upload a rendered Manim .mp4 to Firebase Storage and record it in
the top-level `videos` Firestore collection, keyed by uid.
"""

import os
import glob
import logging
from app.storage.firebase_client import db, bucket
from firebase_admin import firestore

logger = logging.getLogger(__name__)


def find_rendered_mp4(output_dir, scene_filename_stem=None):
    """
    Manim's --media_dir output nests files under
    <output_dir>/videos/<scene_filename>/<quality>/<SceneClassName>.mp4
    so we glob for it rather than hardcoding the path -- the quality
    folder name changes depending on -pql vs -qh.
    """
    pattern = os.path.join(output_dir, "videos", "**", "PhysicsScene.mp4")
    matches = glob.glob(pattern, recursive=True)
    return matches[0] if matches else None


def upload_manim_render(uid, episode_number, output_dir="renders"):
    """Legacy function - kept for backward compatibility."""
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
    try:
        # If video_path is None or doesn't exist, try to find it
        if video_path is None or not os.path.exists(video_path):
            local_path = find_rendered_mp4(output_dir, f"scene_ep_{episode_number}")
            if not local_path:
                logger.error(f"No rendered file found for episode {episode_number}")
                return None
            video_path = local_path
        
        if not os.path.exists(video_path):
            logger.error(f"Video file not found: {video_path}")
            return None

        # Create the Firestore doc first so we have an ID to name the Storage path with
        video_doc_ref = db.collection("videos").document()
        video_id = video_doc_ref.id

        blob_path = f"videos/{uid}/{video_id}.mp4"
        blob = bucket.blob(blob_path)
        
        # Upload the video
        blob.upload_from_filename(video_path)
        blob.make_public()

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
        
        if question_title:
            doc_data["questionTitle"] = question_title

        video_doc_ref.set(doc_data)

        logger.info(f"Uploaded and recorded video {video_id} -> {blob.public_url}")
        
        return {
            "doc_id": video_id,
            "video_url": blob.public_url,
            **doc_data
        }

    except Exception as e:
        logger.error(f"Error uploading episode video: {e}", exc_info=True)
        return None
"""
Video API endpoints for PageSpark
"""
from fastapi import APIRouter, HTTPException, Query, Depends
from fastapi.responses import FileResponse
import os
from typing import Optional
from app.storage.cloudinary_storage import (
    get_user_videos, 
    get_lesson_videos, 
    delete_video,
    increment_view_count,
    get_video_from_cache,
    save_to_cache
)
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/videos", tags=["videos"])


@router.get("/user/{uid}")
async def list_user_videos(uid: str, limit: int = Query(50, ge=1, le=100)):
    """
    Get all videos for a specific user.
    """
    try:
        videos = get_user_videos(uid, limit)
        return {
            "status": "success",
            "count": len(videos),
            "videos": videos
        }
    except Exception as e:
        logger.error(f"Error listing videos: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/lesson/{lesson_id}")
async def list_lesson_videos(lesson_id: str):
    """
    Get all videos for a specific lesson.
    """
    try:
        videos = get_lesson_videos(lesson_id)
        return {
            "status": "success",
            "count": len(videos),
            "videos": videos
        }
    except Exception as e:
        logger.error(f"Error listing lesson videos: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{doc_id}/view")
async def track_view(doc_id: str):
    """
    Increment view count for a video.
    """
    try:
        success = increment_view_count(doc_id)
        if not success:
            raise HTTPException(status_code=404, detail="Video not found")
        return {"status": "success", "message": "View counted"}
    except Exception as e:
        logger.error(f"Error tracking view: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{doc_id}")
async def delete_video_endpoint(doc_id: str, public_id: str = Query(...)):
    """
    Delete a video by its Firestore doc ID and Cloudinary public ID.
    """
    try:
        success = delete_video(doc_id, public_id)
        if not success:
            raise HTTPException(status_code=404, detail="Video not found")
        return {"status": "success", "message": "Video deleted"}
    except Exception as e:
        logger.error(f"Error deleting video: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/cache/{content_hash}")
async def check_cache(content_hash: str):
    """
    Check if a video is cached.
    """
    try:
        video = get_video_from_cache(content_hash)
        if video:
            return {"status": "hit", "video": video}
        return {"status": "miss"}
    except Exception as e:
        logger.error(f"Error checking cache: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/local/{filename}")
async def serve_local_video(filename: str):
    """
    Serve a local video file (fallback when Cloudinary is unavailable).
    """
    video_path = os.path.join("renders", "videos_archive", filename)
    if not os.path.exists(video_path):
        raise HTTPException(status_code=404, detail="Video not found")
    
    return FileResponse(
        video_path,
        media_type="video/mp4",
        headers={
            "Content-Disposition": f"inline; filename={filename}",
            "Accept-Ranges": "bytes",
            "Cache-Control": "public, max-age=86400",
        }
    )
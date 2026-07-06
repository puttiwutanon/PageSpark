"""
Cloudinary Storage for videos + Firestore for metadata + Redis for caching
"""
import os
import logging
import glob
import hashlib
import cloudinary
import cloudinary.uploader
from datetime import datetime
from typing import Optional
import redis
from dotenv import load_dotenv
from firebase_admin import firestore
from app.storage.firebase_client import db

load_dotenv()

logger = logging.getLogger(__name__)

# ── Cloudinary Config ──
cloudinary.config(
    cloud_name=os.environ.get("CLOUDINARY_CLOUD_NAME"),
    api_key=os.environ.get("CLOUDINARY_API_KEY"),
    api_secret=os.environ.get("CLOUDINARY_API_SECRET"),
    secure=True
)
logger.info(f"✅ Cloudinary configured with cloud: {os.environ.get('CLOUDINARY_CLOUD_NAME')}")

# ── Redis Config (for caching) ──
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379")
redis_client = None

try:
    if "upstash.io" in REDIS_URL:
        import urllib.parse
        parsed = urllib.parse.urlparse(REDIS_URL)
        password = parsed.password
        hostname = parsed.hostname
        port = parsed.port or 6379
        
        redis_client = redis.Redis(
            host=hostname,
            port=port,
            password=password,
            ssl=True,
            ssl_cert_reqs=None,
            decode_responses=True,
            socket_timeout=5,
            socket_connect_timeout=5,
        )
        redis_client.ping()
        logger.info(f"✅ Redis connected successfully to {hostname}:{port} with SSL!")
    else:
        redis_client = redis.from_url(REDIS_URL, decode_responses=True)
        redis_client.ping()
        logger.info("✅ Redis connected successfully (local)!")
        
except Exception as e:
    logger.warning(f"⚠️ Redis connection failed: {e}. Caching disabled.")
    redis_client = None

# ── Firestore References ──
videos_ref = db.collection("videos")
lessons_ref = db.collection("lessons")
cache_entries_ref = db.collection("cache_entries")

# ── Local Video Storage (fallback) ──
VIDEO_STORAGE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "renders", "videos_archive")
os.makedirs(VIDEO_STORAGE_DIR, exist_ok=True)


def generate_content_hash(image_data: bytes) -> str:
    """Generate a content hash for deduplication."""
    return hashlib.md5(image_data).hexdigest()


def create_or_get_lesson(uid: str, lesson_id: str) -> dict:
    """
    Create a lesson if it doesn't exist, or get existing one.
    """
    doc_ref = lessons_ref.document(lesson_id)
    doc = doc_ref.get()
    
    if doc.exists:
        return {"id": doc.id, **doc.to_dict()}
    else:
        # Create new lesson
        lesson_data = {
            "uid": uid,
            "lessonId": lesson_id,
            "title": f"Lesson {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "sourceType": "textbook",
            "createdAt": firestore.SERVER_TIMESTAMP,
            "updatedAt": firestore.SERVER_TIMESTAMP,
            "episodeCount": 0,
            "metadata": {},
            "statistics": {
                "totalViews": 0,
                "totalLikes": 0,
                "averageRating": 0
            }
        }
        doc_ref.set(lesson_data)
        logger.info(f"✅ Created new lesson: {lesson_id}")
        return {"id": lesson_id, **lesson_data}


def find_latest_rendered_video(output_dir: str = "renders") -> Optional[str]:
    """
    Find the most recently rendered video file (1920p60 only).
    """
    # Only look for 1920p60 quality
    pattern = os.path.join(output_dir, "videos", "**", "1920p60", "PhysicsScene.mp4")
    matches = glob.glob(pattern, recursive=True)
    
    if not matches:
        logger.warning(f"❌ No 1920p60 video found in {output_dir}")
        return None
    
    # Sort by modification time (newest first)
    matches.sort(key=os.path.getmtime, reverse=True)
    latest = matches[0]
    
    logger.info(f"✅ Found latest 1920p60 video: {latest}")
    logger.info(f"   Modified: {datetime.fromtimestamp(os.path.getmtime(latest))}")
    
    return latest


def upload_episode_video(
    video_path: str,
    uid: str,
    episode_number: int,
    lesson_id: Optional[str] = None,
    question_title: Optional[str] = None,
    output_dir: str = "renders",
    **kwargs
) -> Optional[dict]:
    """
    Upload video to Cloudinary and save metadata to Firestore.
    """
    logger.info(f"📤 ===== STARTING UPLOAD for episode {episode_number} =====")
    logger.info(f"   uid={uid}, lesson_id={lesson_id}")
    
    try:
        # ── STEP 1: Use the provided video path DIRECTLY ──────────────────
        if video_path is None or not os.path.exists(video_path):
            logger.error(f"❌ Video file not found: {video_path}")
            return None
        
        # Check if it's the final combined video (in final/ directory)
        is_final_video = "final" in video_path or "episode_" in os.path.basename(video_path)
        
        if is_final_video:
            logger.info(f"📹 Uploading FINAL combined video: {video_path}")
        else:
            logger.info(f"📹 Uploading raw video: {video_path}")

        # Get file info
        file_size = os.path.getsize(video_path)
        file_mtime = os.path.getmtime(video_path)
        logger.info(f"📹 Video file size: {file_size / (1024*1024):.2f} MB")
        logger.info(f"📹 Video modified: {datetime.fromtimestamp(file_mtime)}")

        # ── STEP 2: Upload to Cloudinary ─────────────────────────────────────
        logger.info("⏳ Uploading to Cloudinary...")
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        suffix = "final" if is_final_video else "raw"
        public_id = f"pagespark/{uid}/episode_{episode_number}_{suffix}_{timestamp}"
        
        result = cloudinary.uploader.upload(
            video_path,
            resource_type="video",
            public_id=public_id,
            use_filename=True,
            unique_filename=True,
            overwrite=False,
            transformation=[
                {"quality": "auto:good"},
                {"format": "mp4"},
                {"fps": 30}
            ],
        )
        
        video_url = result["secure_url"]
        cloudinary_public_id = result["public_id"]
        video_duration = result.get("duration", 0)
        
        logger.info(f"✅ Uploaded to Cloudinary!")
        logger.info(f"   URL: {video_url}")
        logger.info(f"   Duration: {video_duration}s")

        # ── STEP 3: Ensure Lesson exists ─────────────────────────────────────
        if lesson_id:
            lesson = create_or_get_lesson(uid, lesson_id)
            logger.info(f"📚 Lesson: {lesson.get('id')} - {lesson.get('title')}")
            
            lessons_ref.document(lesson_id).update({
                "episodeCount": firestore.Increment(1),
                "updatedAt": firestore.SERVER_TIMESTAMP
            })

        # ── STEP 4: Save to Firestore ────────────────────────────────────────
        doc_data = {
            "uid": uid,
            "episodeNumber": episode_number,
            "title": kwargs.get("title", f"Episode {episode_number}"),
            "questionTitle": question_title,
            "description": kwargs.get("description", ""),
            
            # Cloudinary links
            "cloudinaryPublicId": cloudinary_public_id,
            "videoUrl": video_url,
            "videoDuration": video_duration,
            "fileSize": file_size,
            "localFilePath": video_path,
            "videoQuality": "final_combined" if is_final_video else "raw_manim",
            "isFinalVideo": is_final_video,
            
            # Generation metadata
            "contentHash": kwargs.get("content_hash", None),
            "generationTime": kwargs.get("generation_time", 0),
            "manimCodeVersion": kwargs.get("manim_code_version", "1.0.0"),
            "aiModel": kwargs.get("ai_model", "gemini-2.5-flash"),
            
            # Status
            "status": "completed",
            "errorMessage": None,
            
            # Timestamps
            "createdAt": firestore.SERVER_TIMESTAMP,
            "updatedAt": firestore.SERVER_TIMESTAMP,
            "renderedAt": firestore.SERVER_TIMESTAMP,
            
            # Analytics
            "viewCount": 0,
            "likeCount": 0,
            "rating": 0,
            "completionRate": 0,
            "lastViewedAt": None,
            
            # Relationships
            "lessonId": lesson_id,
            
            # Caching
            "cacheHit": False,
            "originalRequest": kwargs.get("original_request", {})
        }
        
        doc_ref = videos_ref.document()
        doc_ref.set(doc_data)
        doc_id = doc_ref.id
        
        logger.info(f"✅ Saved to Firestore!")
        logger.info(f"   Document ID: {doc_id}")
        logger.info(f"✅ ===== UPLOAD COMPLETE for episode {episode_number} =====")
        
        return {
            "doc_id": doc_id,
            "video_url": video_url,
            "public_id": cloudinary_public_id,
            **doc_data
        }

    except Exception as e:
        logger.error(f"❌ Error uploading to Cloudinary: {e}", exc_info=True)
        return None


def get_video_from_cache(content_hash: str) -> Optional[dict]:
    """Check if video exists in Redis cache."""
    if not redis_client:
        return None
        
    try:
        doc_id = redis_client.get(f"video_cache:{content_hash}")
        if doc_id:
            doc = videos_ref.document(doc_id).get()
            if doc.exists:
                data = doc.to_dict()
                data["id"] = doc.id
                logger.info(f"✅ Cache HIT! Returning cached video")
                
                try:
                    cache_entries_ref.document(content_hash).set({
                        "contentHash": content_hash,
                        "videoId": doc_id,
                        "hitCount": firestore.Increment(1),
                        "lastHitAt": firestore.SERVER_TIMESTAMP
                    }, merge=True)
                except:
                    pass
                
                return data
    except Exception as e:
        logger.warning(f"Redis cache read failed: {e}")
    
    logger.info("❌ Cache MISS")
    return None


def save_to_cache(content_hash: str, doc_id: str, ttl_days: int = 30):
    """Save video ID to Redis cache."""
    if not redis_client:
        return
        
    try:
        redis_client.setex(
            f"video_cache:{content_hash}",
            ttl_days * 86400,
            doc_id
        )
        
        try:
            cache_entries_ref.document(content_hash).set({
                "contentHash": content_hash,
                "videoId": doc_id,
                "hitCount": 0,
                "createdAt": firestore.SERVER_TIMESTAMP,
                "expiresAt": datetime.utcnow().timestamp() + (ttl_days * 86400)
            }, merge=True)
        except:
            pass
        
        logger.info(f"📦 Cached video {doc_id} with hash {content_hash[:8]}...")
    except Exception as e:
        logger.warning(f"Redis cache save failed: {e}")


def get_user_videos(uid: str, limit: int = 50) -> list:
    """Get all videos for a user from Firestore."""
    try:
        videos = videos_ref.where("uid", "==", uid).order_by(
            "createdAt", direction=firestore.Query.DESCENDING
        ).limit(limit).stream()
        
        return [{"id": doc.id, **doc.to_dict()} for doc in videos]
    except Exception as e:
        logger.error(f"Error getting user videos: {e}")
        return []


def get_lesson_videos(lesson_id: str) -> list:
    """Get all videos for a specific lesson."""
    try:
        videos = videos_ref.where("lessonId", "==", lesson_id).order_by(
            "episodeNumber"
        ).stream()
        
        return [{"id": doc.id, **doc.to_dict()} for doc in videos]
    except Exception as e:
        logger.error(f"Error getting lesson videos: {e}")
        return []


def increment_view_count(doc_id: str) -> bool:
    """Increment view count for a video."""
    try:
        videos_ref.document(doc_id).update({
            "viewCount": firestore.Increment(1),
            "lastViewedAt": firestore.SERVER_TIMESTAMP
        })
        return True
    except Exception as e:
        logger.error(f"Error incrementing view count: {e}")
        return False


def delete_video(doc_id: str, public_id: str) -> bool:
    """Delete video from Cloudinary and Firestore."""
    try:
        cloudinary.uploader.destroy(public_id, resource_type="video")
        videos_ref.document(doc_id).delete()
        logger.info(f"🗑️ Deleted video: {doc_id}")
        return True
    except Exception as e:
        logger.error(f"Error deleting video: {e}")
        return False
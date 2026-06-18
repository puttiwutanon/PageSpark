"""
Upload a rendered Manim .mp4 to Firebase Storage and record it in
the top-level `videos` Firestore collection, keyed by uid.
"""

import os
import glob
from app.storage.firebase_client import db, bucket
from firebase_admin import firestore


def find_rendered_mp4(output_dir, scene_filename_stem):
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
    local_path = find_rendered_mp4(output_dir, f"scene_ep_{episode_number}")
    if not local_path:
        print(f"No rendered file found for episode {episode_number}")
        return None

    # Create the Firestore doc first so we have an ID to name the Storage path with
    video_doc_ref = db.collection("videos").document()
    video_id = video_doc_ref.id

    blob_path = f"videos/{uid}/{video_id}.mp4"
    blob = bucket.blob(blob_path)
    blob.upload_from_filename(local_path)
    blob.make_public()  # fine for local testing; tighten with Storage rules before shipping

    video_doc_ref.set({
        "uid": uid,
        "episodeNumber": episode_number,
        "status": "manim_done",
        "manimVideoUrl": blob.public_url,
        "createdAt": firestore.SERVER_TIMESTAMP,
    })

    print(f"Uploaded and recorded video {video_id} -> {blob.public_url}")
    return video_id
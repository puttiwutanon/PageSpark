"""
Single shared initialization of firebase_admin for the whole app.
Handles Authentication, Firestore, and Cloudinary integration.
"""
import os
import logging
import firebase_admin
from firebase_admin import credentials, firestore, auth
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

current_dir = os.path.dirname(os.path.abspath(__file__))

# Try multiple possible paths for the service account key
possible_paths = [
    os.path.join(current_dir, "..", "..", "serviceAccountKey.json"),
    os.path.join(current_dir, "..", "..", "..", "serviceAccountKey.json"),
    os.path.join(current_dir, "..", "serviceAccountKey.json"),
    os.path.join(os.path.dirname(os.path.dirname(current_dir)), "serviceAccountKey.json"),
]

service_account_path = None
for path in possible_paths:
    if os.path.exists(path):
        service_account_path = path
        break

if service_account_path is None:
    # Fallback: try to use environment variable for credentials
    cred_json = os.environ.get("FIREBASE_CREDENTIALS")
    if cred_json:
        import json
        cred_dict = json.loads(cred_json)
        cred = credentials.Certificate(cred_dict)
        logger.info("✅ Firebase initialized using environment variable credentials")
    else:
        raise FileNotFoundError(
            "serviceAccountKey.json not found in any expected location. "
            f"Checked: {possible_paths}"
        )
else:
    cred = credentials.Certificate(service_account_path)
    logger.info(f"✅ Firebase initialized using service account: {service_account_path}")

# Initialize Firebase
firebase_admin.initialize_app(cred)

# Export Firestore client
db = firestore.client()

logger.info("✅ Firebase Firestore ready!")

# Helper functions for Firestore operations
def get_user(uid: str) -> dict | None:
    """Get user data from Firestore."""
    try:
        doc = db.collection("users").document(uid).get()
        if doc.exists:
            return {"id": doc.id, **doc.to_dict()}
        return None
    except Exception as e:
        logger.error(f"Error getting user: {e}")
        return None

def create_user(uid: str, data: dict) -> dict:
    """Create or update user in Firestore."""
    try:
        doc_ref = db.collection("users").document(uid)
        doc_ref.set(data, merge=True)
        return {"id": uid, **data}
    except Exception as e:
        logger.error(f"Error creating user: {e}")
        return None
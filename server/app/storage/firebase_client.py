"""
Single shared initialization of firebase_admin for the whole app.
Every other module should import `db` and `bucket` from here instead
of calling firebase_admin.initialize_app() themselves -- Firebase
throws if you initialize the same app twice in one process.
"""

import os
import logging
import firebase_admin
from firebase_admin import credentials, firestore, storage

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
    else:
        raise FileNotFoundError(
            "serviceAccountKey.json not found in any expected location. "
            f"Checked: {possible_paths}"
        )
else:
    cred = credentials.Certificate(service_account_path)

# Get bucket name from environment or use default
BUCKET_NAME = os.environ.get("FIREBASE_STORAGE_BUCKET", "pagespark-39612.appspot.com")

firebase_admin.initialize_app(cred, {
    'storageBucket': BUCKET_NAME
})

db = firestore.client()
bucket = storage.bucket()

logger.info(f"Firebase initialized with bucket: {BUCKET_NAME}")
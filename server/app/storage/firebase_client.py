"""
Single shared initialization of firebase_admin for the whole app.
Every other module should import `db` and `bucket` from here instead
of calling firebase_admin.initialize_app() themselves -- Firebase
throws if you initialize the same app twice in one process.
"""

import os
import firebase_admin
from firebase_admin import credentials, firestore, storage

current_dir = os.path.dirname(os.path.abspath(__file__))
# adjust this path to wherever your service account key actually lives
service_account_path = os.path.join(current_dir, "..", "..", "serviceAccountKey.json")

cred = credentials.Certificate(service_account_path)
firebase_admin.initialize_app(cred, {
    'storageBucket': 'pagespark-39612.appspot.com'  # <- replace with your real bucket
})

db = firestore.client()
bucket = storage.bucket()
import os
import firebase_admin
from firebase_admin import credentials, firestore, storage

cred = credentials.Certificate(os.getenv("GOOGLE_APPLICATION_CREDENTIALS"))
firebase_admin.initialize_app(cred)

db = firestore.client()
bucket = storage.bucket()  # Use your bucket name if not default

def add_document(collection, data, doc_id=None):
    ref = db.collection(collection).document(doc_id) if doc_id else db.collection(collection).document()
    ref.set(data)
    return ref.id

def get_document(collection, doc_id):
    return db.collection(collection).document(doc_id).get().to_dict()

def update_document(collection, doc_id, data):
    db.collection(collection).document(doc_id).update(data)

def query_collection(collection, filters=None):
    query = db.collection(collection)
    if filters:
        for field, op, value in filters:
            query = query.where(field, op, value)
    return [doc.to_dict() for doc in query.stream()]

def upload_file(file_path, storage_path):
    blob = bucket.blob(storage_path)
    blob.upload_from_filename(file_path)
    return blob.public_url

def download_file(storage_path, local_path):
    blob = bucket.blob(storage_path)
    blob.download_to_filename(local_path)

# Add more for auth if needed (e.g., firebase_admin.auth)
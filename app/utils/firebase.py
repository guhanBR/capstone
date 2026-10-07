import os
import json
import logging
import firebase_admin
from firebase_admin import credentials, firestore

logger = logging.getLogger(__name__)

_firestore_db = None

def get_firebase_credentials_path():
    """
    Search for Firebase service account key in common paths or environment variables.
    """
    env_path = os.environ.get('FIREBASE_CREDENTIALS')
    if env_path and os.path.exists(env_path):
        return env_path
        
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    possible_filenames = [
        'serviceAccountKey.json',
        'serviceAccountKey.json.json',
        'firebase-key.json'
    ]
    
    for filename in possible_filenames:
        full_path = os.path.join(base_dir, filename)
        if os.path.exists(full_path):
            return full_path
            
    return None

def init_firebase(app=None):
    """
    Initialize Firebase Admin SDK and return Firestore client.
    Supports file path, environment JSON string (FIREBASE_KEY_JSON), and Render Secret Files (/etc/secrets/serviceAccountKey.json).
    """
    global _firestore_db
    
    if _firestore_db is not None:
        return _firestore_db
        
    try:
        cred = None
        # Check for environment variable with raw JSON content
        json_env = os.environ.get('FIREBASE_KEY_JSON') or os.environ.get('FIREBASE_CREDENTIALS_JSON')
        if json_env:
            logger.info("Initializing Firebase Admin SDK from FIREBASE_KEY_JSON environment variable.")
            key_dict = json.loads(json_env)
            cred = credentials.Certificate(key_dict)
        else:
            # Check for Render Secret Files path
            render_secret_path = '/etc/secrets/serviceAccountKey.json'
            cred_path = render_secret_path if os.path.exists(render_secret_path) else get_firebase_credentials_path()
            if cred_path:
                logger.info(f"Initializing Firebase Admin SDK with credentials from: {cred_path}")
                cred = credentials.Certificate(cred_path)

        if cred:
            if not firebase_admin._apps:
                firebase_admin.initialize_app(cred)
            _firestore_db = firestore.client()
            logger.info("Firebase Admin SDK & Firestore database connected successfully!")
        else:
            logger.warning("No Firebase credentials found. Firebase features will be uninitialized.")
    except Exception as e:
        logger.error(f"Failed to initialize Firebase Admin SDK: {e}")
        _firestore_db = None

        
    if app and _firestore_db:
        app.config['FIRESTORE_DB'] = _firestore_db
        
    return _firestore_db

def get_firestore_db():
    """
    Get initialized Firestore database client.
    """
    global _firestore_db
    if _firestore_db is None:
        _firestore_db = init_firebase()
    return _firestore_db


# --- Firestore CRUD Helper Functions ---

def save_document(collection_name, doc_id, data):
    """
    Create or overwrite a document in Firestore.
    """
    db = get_firestore_db()
    if not db:
        raise RuntimeError("Firestore DB client is not initialized.")
    doc_ref = db.collection(collection_name).document(doc_id)
    doc_ref.set(data)
    return doc_id

def get_document(collection_name, doc_id):
    """
    Read a single document by ID from Firestore.
    Returns dictionary of data if found, or None if not found.
    """
    db = get_firestore_db()
    if not db:
        return None
    doc_ref = db.collection(collection_name).document(doc_id)
    doc = doc_ref.get()
    if doc.exists:
        data = doc.to_dict()
        data['id'] = doc.id
        return data
    return None

def get_collection_documents(collection_name):
    """
    Read all documents in a collection.
    Returns list of document data dicts.
    """
    db = get_firestore_db()
    if not db:
        return []
    docs = db.collection(collection_name).stream()
    result = []
    for doc in docs:
        d = doc.to_dict()
        d['id'] = doc.id
        result.append(d)
    return result

def update_document(collection_name, doc_id, updates):
    """
    Update specific fields of an existing document in Firestore.
    """
    db = get_firestore_db()
    if not db:
        raise RuntimeError("Firestore DB client is not initialized.")
    doc_ref = db.collection(collection_name).document(doc_id)
    doc_ref.update(updates)
    return True

def delete_document(collection_name, doc_id):
    """
    Delete a document from Firestore.
    """
    db = get_firestore_db()
    if not db:
        raise RuntimeError("Firestore DB client is not initialized.")
    doc_ref = db.collection(collection_name).document(doc_id)
    doc_ref.delete()
    return True


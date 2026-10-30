import os
import sys
import logging

# Ensure project root is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app import create_app
from app.utils.firebase import get_firestore_db
from app.services.firebase_sync import push_local_to_firestore
from app.models.product import Product
from app.models.user import User

logger = logging.getLogger(__name__)

def seed_firebase_data():
    print("==========================================================")
    print("  SparePro Full Firebase Firestore Data Seeding Utility   ")
    print("==========================================================")

    db = get_firestore_db()
    if not db:
        print("[ERROR] Firebase Firestore client is not initialized. Please check serviceAccountKey.json.")
        return False

    app = create_app('development')
    with app.app_context():
        # Verify local database content, if empty trigger local seed script first
        prod_count = Product.query.count()
        user_count = User.query.count()

        if prod_count == 0 or user_count == 0:
            print("[INFO] Local database empty or incomplete. Running local database seed first...")
            try:
                from seed.seed_data import seed
                seed()
            except Exception as se:
                print(f"[WARNING] Could not execute seed_data.py: {se}")

        print("\n[Seeding] Pushing all 40+ products, images, user credentials, categories, orders, reviews & logs to Firebase Firestore...")
        success = push_local_to_firestore()

        if success:
            print("\n==========================================================")
            print(" SUCCESS: All old & new data, images & credentials seeded to Firebase!")
            print("==========================================================")
            return True
        else:
            print("\n[ERROR] Failed to push data to Firebase Firestore.")
            return False

if __name__ == '__main__':
    seed_firebase_data()


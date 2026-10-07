import os
import sys
import logging
from datetime import datetime, timezone

# Ensure project root is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app.utils.firebase import get_firestore_db, save_document

logger = logging.getLogger(__name__)

def seed_firebase_data():
    print("==========================================================")
    print("      SparePro Firebase Firestore Data Seeding Utility    ")
    print("==========================================================")

    db = get_firestore_db()
    if not db:
        print("[ERROR] Firebase Firestore client is not initialized. Please check serviceAccountKey.json.")
        return False

    now_iso = datetime.now(timezone.utc).isoformat()

    # 1. SEED CATEGORIES
    print("\n[1/4] Seeding Categories to Firestore...")
    categories = [
        {
            "id": "cat_bearings",
            "name": "Bearings",
            "description": "High precision deep groove, angular contact & roller bearings for motor rotors and pump shafts.",
            "status": "active",
            "created_at": now_iso
        },
        {
            "id": "cat_seals",
            "name": "Mechanical Seals",
            "description": "Single spring, cartridge, ceramic & tungsten carbide seals for industrial pumps.",
            "status": "active",
            "created_at": now_iso
        },
        {
            "id": "cat_capacitors",
            "name": "Capacitors",
            "description": "Motor run & start capacitors engineered for continuous duty operation.",
            "status": "active",
            "created_at": now_iso
        },
        {
            "id": "cat_impellers",
            "name": "Impellers",
            "description": "Cast iron, bronze, and stainless steel impellers for centrifugal & submersible pumps.",
            "status": "active",
            "created_at": now_iso
        },
        {
            "id": "cat_shafts",
            "name": "Pump Shafts",
            "description": "Precision ground SS-304 & SS-316 pump drive shafts.",
            "status": "active",
            "created_at": now_iso
        },
        {
            "id": "cat_motor_parts",
            "name": "Motor Parts",
            "description": "Cooling fans, terminal boards, junction boxes, and rotors for electric motors.",
            "status": "active",
            "created_at": now_iso
        }
    ]

    for cat in categories:
        save_document("categories", cat["id"], cat)
        print(f"  + Added Category: {cat['name']}")

    # 2. SEED PRODUCTS
    print("\n[2/4] Seeding Spare Parts Products to Firestore...")
    products = [
        {
            "id": "prod_6203_brg",
            "name": "6203 Deep Groove Ball Bearing",
            "sku": "BRG-6203-OPEN",
            "brand": "SKF",
            "model_number": "6203",
            "description": "Open deep groove ball bearing 17mm x 40mm x 12mm.",
            "specifications": "ID: 17mm, OD: 40mm, Width: 12mm",
            "compatibility": "Fits standard 1 HP electric motors",
            "price": 180.00,
            "discount_price": 160.00,
            "stock_quantity": 45,
            "min_stock_alert": 10,
            "category": "Bearings",
            "status": "active",
            "rating": 4.8,
            "created_at": now_iso
        },
        {
            "id": "prod_6305_brg",
            "name": "6305 Heavy Duty Ball Bearing",
            "sku": "BRG-6305-2RS",
            "brand": "FAG",
            "model_number": "6305-2RS",
            "description": "Rubber sealed deep groove ball bearing 25mm x 62mm x 17mm.",
            "specifications": "ID: 25mm, OD: 62mm, Width: 17mm",
            "compatibility": "Suitable for 3 HP to 5 HP heavy duty motors",
            "price": 380.00,
            "discount_price": 340.00,
            "stock_quantity": 30,
            "min_stock_alert": 8,
            "category": "Bearings",
            "status": "active",
            "rating": 4.9,
            "created_at": now_iso
        },
        {
            "id": "prod_mech_seal_20",
            "name": "20mm Ceramic Mechanical Shaft Seal",
            "sku": "SEAL-CER-20MM",
            "brand": "Burgmann",
            "model_number": "MG1-20",
            "description": "Single elastomer bellows mechanical seal for water pumps.",
            "specifications": "Shaft size: 20mm, Temp: -20C to +120C",
            "compatibility": "Monoblock and centrifugal water pumps",
            "price": 450.00,
            "discount_price": 410.00,
            "stock_quantity": 25,
            "min_stock_alert": 5,
            "category": "Mechanical Seals",
            "status": "active",
            "rating": 4.7,
            "created_at": now_iso
        },
        {
            "id": "prod_cap_36mfd",
            "name": "36 MFD 440V Motor Run Capacitor",
            "sku": "CAP-36MFD-440V",
            "brand": "Tibcon",
            "model_number": "TIB-36-440",
            "description": "Polypropylene film motor run capacitor for single phase motors.",
            "specifications": "36 MFD +/- 5%, Voltage: 440VAC, 50Hz",
            "compatibility": "1.5 HP Submersible and Monoblock pumps",
            "price": 240.00,
            "discount_price": 210.00,
            "stock_quantity": 60,
            "min_stock_alert": 15,
            "category": "Capacitors",
            "status": "active",
            "rating": 4.6,
            "created_at": now_iso
        },
        {
            "id": "prod_impeller_ci",
            "name": "Cast Iron Centrifugal Pump Impeller",
            "sku": "IMP-CI-150MM",
            "brand": "Kirloskar",
            "model_number": "K-IMP-150",
            "description": "Closed type cast iron impeller dynamically balanced.",
            "specifications": "Outer Dia: 150mm, Bore: 22mm",
            "compatibility": "2 HP Centrifugal monoblock pumps",
            "price": 1250.00,
            "discount_price": 1100.00,
            "stock_quantity": 18,
            "min_stock_alert": 4,
            "category": "Impellers",
            "status": "active",
            "rating": 4.9,
            "created_at": now_iso
        },
        {
            "id": "prod_shaft_ss304",
            "name": "SS-304 Precision Drive Shaft",
            "sku": "SHFT-SS304-25X450",
            "brand": "Crompton",
            "model_number": "SHFT-25",
            "description": "Precision ground stainless steel grade 304 drive shaft.",
            "specifications": "Diameter: 25mm, Length: 450mm with keyway",
            "compatibility": "Industrial openwell and monoblock pumps",
            "price": 1850.00,
            "discount_price": 1699.00,
            "stock_quantity": 12,
            "min_stock_alert": 3,
            "category": "Pump Shafts",
            "status": "active",
            "rating": 4.8,
            "created_at": now_iso
        }
    ]

    for prod in products:
        save_document("products", prod["id"], prod)
        print(f"  + Added Product: {prod['name']} (Rs. {prod['price']})")


    # 3. SEED USERS
    print("\n[3/4] Seeding User Accounts to Firestore...")
    users = [
        {
            "id": "usr_admin",
            "name": "System Administrator",
            "email": "admin@sparepro.local",
            "role": "admin",
            "phone": "9998887770",
            "status": "active",
            "created_at": now_iso
        },
        {
            "id": "usr_manager",
            "name": "Operations Manager",
            "email": "manager@sparepro.local",
            "role": "manager",
            "phone": "9998887771",
            "status": "active",
            "created_at": now_iso
        },
        {
            "id": "usr_customer1",
            "name": "Rajesh Kumar",
            "email": "rajesh.kumar@example.com",
            "role": "customer",
            "phone": "9876543210",
            "city": "Coimbatore",
            "status": "active",
            "created_at": now_iso
        }
    ]

    for usr in users:
        save_document("users", usr["id"], usr)
        print(f"  + Added User: {usr['name']} ({usr['role']})")

    # 4. SEED SAMPLE ORDERS
    print("\n[4/4] Seeding Sample Orders to Firestore...")
    orders = [
        {
            "id": "ord_1001",
            "order_number": "SP-ORD-2026-1001",
            "customer_id": "usr_customer1",
            "customer_name": "Rajesh Kumar",
            "customer_email": "rajesh.kumar@example.com",
            "items": [
                {
                    "product_id": "prod_impeller_ci",
                    "product_name": "Cast Iron Centrifugal Pump Impeller",
                    "quantity": 1,
                    "unit_price": 1100.00
                },
                {
                    "product_id": "prod_6203_brg",
                    "product_name": "6203 Deep Groove Ball Bearing",
                    "quantity": 2,
                    "unit_price": 160.00
                }
            ],
            "total_amount": 1420.00,
            "status": "delivered",
            "payment_status": "paid",
            "payment_method": "UPI",
            "created_at": now_iso
        }
    ]

    for ord_data in orders:
        save_document("orders", ord_data["id"], ord_data)
        print(f"  + Added Order: #{ord_data['order_number']} (Total: Rs. {ord_data['total_amount']})")


    print("\n==========================================================")
    print(" SUCCESS: Firebase Firestore database seeded with sample data!")
    print("==========================================================")
    return True

if __name__ == '__main__':
    seed_firebase_data()

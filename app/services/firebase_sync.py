import logging
from datetime import datetime, timezone
from app import db
from app.utils.firebase import get_firestore_db, get_collection_documents, save_document
from app.models.category import Category
from app.models.product import Product
from app.models.user import User
from app.models.order import Order, OrderItem
from app.models.address import Address
from app.models.review import Review
from app.models.audit_log import AuditLog
from werkzeug.security import generate_password_hash

logger = logging.getLogger(__name__)

def sync_firestore_to_local():
    """
    Sync data from Firebase Firestore collections into the local application database.
    Ensures hosted deployments retain all users, credentials, categories, products with images, and orders.
    """
    try:
        from flask import current_app
        if current_app and current_app.config.get('TESTING'):
            return False
    except Exception:
        pass

    db_firestore = get_firestore_db()
    if not db_firestore:
        logger.warning("Firebase Firestore is not initialized. Sync skipped.")
        return False

    try:
        # 1. Sync User Accounts & Credentials from Firestore
        fs_users = get_collection_documents('users')
        for fu in fs_users:
            email = (fu.get('email') or '').strip().lower()
            if not email:
                continue

            user = User.query.filter_by(email=email).first()
            pwd_hash = fu.get('password_hash')
            if not pwd_hash:
                # Fallback password hash generation if plain text or default is set
                plain = fu.get('plain_password') or fu.get('password')
                if plain:
                    pwd_hash = generate_password_hash(plain)
                elif fu.get('role') == 'admin':
                    pwd_hash = generate_password_hash('Admin@12345')
                elif fu.get('role') == 'manager':
                    pwd_hash = generate_password_hash('Manager@12345')
                elif fu.get('role') == 'employee':
                    pwd_hash = generate_password_hash('Employee@12345')
                else:
                    pwd_hash = generate_password_hash('Customer@123')

            if not user:
                user = User(
                    name=fu.get('name', 'User'),
                    email=email,
                    phone=fu.get('phone', '9998887770'),
                    role=fu.get('role', 'customer'),
                    status=fu.get('status', 'active'),
                    password_hash=pwd_hash,
                    theme_preference=fu.get('theme_preference', 'dark')
                )
                db.session.add(user)
            else:
                user.name = fu.get('name', user.name)
                user.phone = fu.get('phone', user.phone)
                user.role = fu.get('role', user.role)
                user.status = fu.get('status', user.status)
                user.theme_preference = fu.get('theme_preference', user.theme_preference)
                if fu.get('password_hash'):
                    user.password_hash = fu.get('password_hash')
        db.session.commit()

        # 2. Sync Categories from Firestore
        fs_categories = get_collection_documents('categories')
        for fc in fs_categories:
            cat_name = fc.get('name')
            if not cat_name:
                continue
            cat = Category.query.filter_by(name=cat_name).first()
            if not cat:
                cat = Category(
                    name=cat_name,
                    description=fc.get('description', ''),
                    status=fc.get('status', 'active')
                )
                db.session.add(cat)
            else:
                cat.description = fc.get('description', cat.description)
                cat.status = fc.get('status', cat.status)
        db.session.commit()

        # 3. Sync Products & Images from Firestore
        fs_products = get_collection_documents('products')
        for fp in fs_products:
            sku = fp.get('sku') or fp.get('id')
            if not sku:
                continue

            # Map category name to category_id
            cat_name = fp.get('category')
            category_id = 1
            if cat_name:
                cat_obj = Category.query.filter_by(name=cat_name).first()
                if cat_obj:
                    category_id = cat_obj.id

            prod = Product.query.filter_by(sku=sku).first()
            img_val = fp.get('image') or fp.get('image_url') or 'placeholder.svg'

            if not prod:
                prod = Product(
                    name=fp.get('name', 'Sample Spare Part'),
                    sku=sku,
                    brand=fp.get('brand', 'SparePro'),
                    model_number=fp.get('model_number', ''),
                    description=fp.get('description', ''),
                    specifications=fp.get('specifications', ''),
                    compatibility=fp.get('compatibility', ''),
                    price=float(fp.get('price', 0.0)),
                    discount_price=float(fp.get('discount_price', 0.0)) if fp.get('discount_price') else None,
                    stock_quantity=int(fp.get('stock_quantity', fp.get('stock', 10))),
                    minimum_stock_level=int(fp.get('minimum_stock_level', fp.get('min_stock_alert', 5))),
                    category_id=category_id,
                    image=img_val,
                    status=fp.get('status', 'active')
                )
                db.session.add(prod)
            else:
                prod.name = fp.get('name', prod.name)
                prod.brand = fp.get('brand', prod.brand)
                prod.model_number = fp.get('model_number', prod.model_number)
                prod.description = fp.get('description', prod.description)
                prod.specifications = fp.get('specifications', prod.specifications)
                prod.compatibility = fp.get('compatibility', prod.compatibility)
                prod.price = float(fp.get('price', prod.price))
                if fp.get('discount_price') is not None:
                    prod.discount_price = float(fp.get('discount_price'))
                prod.stock_quantity = int(fp.get('stock_quantity', fp.get('stock', prod.stock_quantity)))
                if fp.get('minimum_stock_level') is not None:
                    prod.minimum_stock_level = int(fp.get('minimum_stock_level'))
                if fp.get('image'):
                    prod.image = fp.get('image')
                prod.status = fp.get('status', prod.status)
        db.session.commit()

        logger.info("Firebase Firestore data successfully synchronized with local app database!")
        return True
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error syncing Firebase Firestore data: {e}")
        return False

def push_local_to_firestore():
    """
    Push all local application models (Categories, Products, Users & Credentials, Orders, Addresses, Reviews, Audit Logs)
    to Firebase Firestore so hosted platforms can access all credentials, images, and data.
    """
    db_firestore = get_firestore_db()
    if not db_firestore:
        logger.error("Firestore DB client is not initialized.")
        return False

    now_iso = datetime.now(timezone.utc).isoformat()

    try:
        logger.info("Pushing User Accounts & Credentials to Firestore...")
        users = User.query.all()
        for user in users:
            plain_hint = "Admin@12345" if user.role == 'admin' else ("Manager@12345" if user.role == 'manager' else ("Employee@12345" if user.role == 'employee' else "Customer@123"))
            save_document('users', f"usr_{user.id}", {
                'id': f"usr_{user.id}",
                'sql_id': user.id,
                'name': user.name,
                'email': user.email,
                'phone': user.phone,
                'role': user.role,
                'status': user.status,
                'password_hash': user.password_hash,
                'credentials_note': f"Login Email: {user.email} | Default Password: {plain_hint}",
                'theme_preference': user.theme_preference,
                'created_at': user.created_at.isoformat() if user.created_at else now_iso
            })

        logger.info("Pushing Categories to Firestore...")
        categories = Category.query.all()
        for cat in categories:
            save_document('categories', f"cat_{cat.id}", {
                'id': f"cat_{cat.id}",
                'sql_id': cat.id,
                'name': cat.name,
                'description': cat.description,
                'status': cat.status,
                'created_at': cat.created_at.isoformat() if hasattr(cat, 'created_at') and cat.created_at else now_iso
            })

        logger.info("Pushing Products & Images to Firestore...")
        products = Product.query.all()
        for prod in products:
            doc_id = prod.sku or f"prod_{prod.id}"
            save_document('products', doc_id, {
                'id': doc_id,
                'sql_id': prod.id,
                'name': prod.name,
                'sku': prod.sku,
                'brand': prod.brand,
                'model_number': prod.model_number,
                'description': prod.description,
                'specifications': prod.specifications,
                'compatibility': prod.compatibility,
                'price': float(prod.price),
                'discount_price': float(prod.discount_price) if prod.discount_price else None,
                'stock_quantity': prod.stock_quantity,
                'minimum_stock_level': prod.minimum_stock_level,
                'category': prod.category.name if prod.category else 'General',
                'category_id': prod.category_id,
                'image': prod.image,
                'image_url': prod.image_url,
                'status': prod.status,
                'rating': prod.average_rating,
                'review_count': prod.review_count,
                'created_at': prod.created_at.isoformat() if prod.created_at else now_iso
            })

        logger.info("Pushing Orders & Order Items to Firestore...")
        orders = Order.query.all()
        for order in orders:
            items_data = [
                {
                    'product_id': item.product_id,
                    'product_name': item.product_name,
                    'sku': item.sku,
                    'quantity': item.quantity,
                    'unit_price': float(item.unit_price),
                    'subtotal': float(item.subtotal)
                }
                for item in order.items
            ]
            save_document('orders', f"ord_{order.id}", {
                'id': f"ord_{order.id}",
                'sql_id': order.id,
                'order_number': order.order_number,
                'user_id': order.user_id,
                'customer_name': order.user.name if order.user else 'Customer',
                'customer_email': order.user.email if order.user else '',
                'subtotal': float(order.subtotal),
                'discount': float(order.discount),
                'shipping_charge': float(order.shipping_charge),
                'total_amount': float(order.total_amount),
                'payment_method': order.payment_method,
                'payment_status': order.payment_status,
                'order_status': order.order_status,
                'items': items_data,
                'created_at': order.created_at.isoformat() if order.created_at else now_iso
            })

        logger.info("Pushing Delivery Addresses to Firestore...")
        addresses = Address.query.all()
        for addr in addresses:
            save_document('addresses', f"addr_{addr.id}", {
                'id': f"addr_{addr.id}",
                'sql_id': addr.id,
                'user_id': addr.user_id,
                'full_name': addr.full_name,
                'phone': addr.phone,
                'address_line_1': addr.address_line_1,
                'address_line_2': addr.address_line_2,
                'city': addr.city,
                'state': addr.state,
                'postal_code': addr.postal_code,
                'country': addr.country,
                'is_default': addr.is_default
            })

        logger.info("Pushing Product Reviews to Firestore...")
        reviews = Review.query.all()
        for rev in reviews:
            save_document('reviews', f"rev_{rev.id}", {
                'id': f"rev_{rev.id}",
                'sql_id': rev.id,
                'user_id': rev.user_id,
                'product_id': rev.product_id,
                'order_id': rev.order_id,
                'rating': rev.rating,
                'review_text': rev.review_text,
                'status': rev.status,
                'created_at': rev.created_at.isoformat() if rev.created_at else now_iso
            })

        logger.info("Pushing Audit Logs to Firestore...")
        logs = AuditLog.query.all()
        for log in logs:
            save_document('audit_logs', f"log_{log.id}", {
                'id': f"log_{log.id}",
                'sql_id': log.id,
                'user_id': log.user_id,
                'action': log.action,
                'entity_type': log.entity_type,
                'description': log.description,
                'created_at': log.created_at.isoformat() if log.created_at else now_iso
            })

        logger.info("SUCCESS: All local database models, images, and credentials successfully pushed to Firebase Firestore!")
        return True
    except Exception as e:
        logger.error(f"Error pushing data to Firebase Firestore: {e}")
        return False


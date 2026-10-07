import logging
from app import db
from app.utils.firebase import get_firestore_db, get_collection_documents, save_document
from app.models.category import Category
from app.models.product import Product
from app.models.user import User
from app.models.order import Order

logger = logging.getLogger(__name__)

def sync_firestore_to_local():
    """
    Sync data from Firebase Firestore collections into the application's database.
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
        # 1. Sync Categories from Firestore
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

        # 2. Sync Products from Firestore
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
                    minimum_stock_level=int(fp.get('min_stock_alert', 5)),
                    category_id=category_id,
                    status=fp.get('status', 'active')
                )
                db.session.add(prod)
            else:
                prod.name = fp.get('name', prod.name)
                prod.price = float(fp.get('price', prod.price))
                prod.stock_quantity = int(fp.get('stock_quantity', fp.get('stock', prod.stock_quantity)))
                prod.status = fp.get('status', prod.status)
        db.session.commit()

        logger.info("Firebase Firestore data successfully synchronized with Flask app models!")
        return True
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error syncing Firebase Firestore data: {e}")
        return False

def push_local_to_firestore():
    """
    Push local application models to Firebase Firestore.
    """
    db_firestore = get_firestore_db()
    if not db_firestore:
        return False

    try:
        # Push Categories
        categories = Category.query.all()
        for cat in categories:
            save_document('categories', f"cat_{cat.id}", {
                'id': f"cat_{cat.id}",
                'name': cat.name,
                'description': cat.description,
                'status': cat.status
            })

        # Push Products
        products = Product.query.all()
        for prod in products:
            save_document('products', prod.sku or f"prod_{prod.id}", {
                'id': prod.sku or f"prod_{prod.id}",
                'name': prod.name,
                'sku': prod.sku,
                'brand': prod.brand,
                'price': float(prod.price),
                'stock_quantity': prod.stock_quantity,
                'category': prod.category.name if prod.category else 'General',
                'status': prod.status
            })
        return True
    except Exception as e:
        logger.error(f"Error pushing data to Firebase Firestore: {e}")
        return False

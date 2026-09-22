from sqlalchemy import or_, and_, asc, desc
from app import db
from app.models.product import Product
from app.models.category import Category
from app.models.inventory import InventoryTransaction
from app.utils.validators import validate_product_data
from app.utils.helpers import log_audit

class ProductService:
    @staticmethod
    def get_products(category_id=None, brand=None, min_price=None, max_price=None,
                     availability=None, min_rating=None, search_query=None,
                     sort_by='newest', status='active', page=1, per_page=12):
        
        query = Product.query

        if status:
            query = query.filter(Product.status == status)

        if category_id:
            query = query.filter(Product.category_id == category_id)

        if brand:
            query = query.filter(Product.brand == brand)

        if min_price is not None and min_price != '':
            try:
                query = query.filter(Product.price >= float(min_price))
            except (ValueError, TypeError):
                pass

        if max_price is not None and max_price != '':
            try:
                query = query.filter(Product.price <= float(max_price))
            except (ValueError, TypeError):
                pass

        if availability == 'in_stock':
            query = query.filter(Product.stock_quantity > 0)
        elif availability == 'low_stock':
            query = query.filter(and_(Product.stock_quantity > 0, Product.stock_quantity <= Product.minimum_stock_level))
        elif availability == 'out_of_stock':
            query = query.filter(Product.stock_quantity <= 0)

        if search_query:
            term = f"%{search_query.strip()}%"
            query = query.filter(or_(
                Product.name.ilike(term),
                Product.sku.ilike(term),
                Product.brand.ilike(term),
                Product.model_number.ilike(term),
                Product.description.ilike(term),
                Product.compatibility.ilike(term)
            ))

        # Sorting logic
        if sort_by == 'price_asc':
            query = query.order_by(asc(Product.price))
        elif sort_by == 'price_desc':
            query = query.order_by(desc(Product.price))
        elif sort_by == 'name_asc':
            query = query.order_by(asc(Product.name))
        elif sort_by == 'name_desc':
            query = query.order_by(desc(Product.name))
        elif sort_by == 'best_selling':
            query = query.order_by(desc(Product.stock_quantity))
        elif sort_by == 'highest_rated':
            query = query.order_by(desc(Product.id))
        elif sort_by == 'oldest':
            query = query.order_by(asc(Product.created_at))
        else: # 'newest'
            query = query.order_by(desc(Product.created_at))

        paginated = query.paginate(page=page, per_page=per_page, error_out=False)
        return paginated

    @staticmethod
    def get_brands():
        brands = db.session.query(Product.brand).filter(Product.status == 'active').distinct().all()
        return [b[0] for b in brands if b[0]]

    @staticmethod
    def get_max_price():
        import math
        max_p = db.session.query(db.func.max(Product.price)).filter(Product.status == 'active').scalar()
        if max_p is not None and float(max_p) > 0:
            return float(math.ceil(float(max_p)))
        return 10000.0

    @staticmethod
    def create_product(data, admin_id):
        valid, errors = validate_product_data(data)
        if not valid:
            return False, errors[0], None

        existing_sku = Product.query.filter_by(sku=data['sku'].strip()).first()
        if existing_sku:
            return False, "A product with this SKU already exists.", None

        try:
            product = Product(
                category_id=int(data['category_id']),
                name=data['name'].strip(),
                sku=data['sku'].strip(),
                brand=data['brand'].strip(),
                model_number=data.get('model_number', '').strip(),
                description=data.get('description', '').strip(),
                specifications=data.get('specifications', '').strip(),
                compatibility=data.get('compatibility', '').strip(),
                price=float(data['price']),
                discount_price=float(data['discount_price']) if data.get('discount_price') else None,
                stock_quantity=int(data.get('stock_quantity', 0)),
                minimum_stock_level=int(data.get('minimum_stock_level', 5)),
                image=data.get('image', 'placeholder.png'),
                status=data.get('status', 'active')
            )
            db.session.add(product)
            db.session.flush()

            # Record initial inventory transaction if stock > 0
            if product.stock_quantity > 0:
                inv_trans = InventoryTransaction(
                    product_id=product.id,
                    transaction_type='Purchase',
                    quantity=product.stock_quantity,
                    previous_quantity=0,
                    new_quantity=product.stock_quantity,
                    reference_type='Initial Stock',
                    notes='Product initial stock creation'
                )
                db.session.add(inv_trans)

            db.session.commit()
            log_audit(admin_id, 'CREATE', 'Product', product.id, f"Created product {product.name} ({product.sku})")
            return True, "Product created successfully!", product
        except Exception as e:
            db.session.rollback()
            return False, f"Failed to create product: {str(e)}", None

    @staticmethod
    def update_product(product_id, data, admin_id):
        # Always fetch fresh from DB — bypass any identity-map cache
        product = db.session.get(Product, product_id)
        if not product:
            return False, "Product not found.", None

        valid, errors = validate_product_data(data)
        if not valid:
            return False, errors[0], None

        # Business rule: discount price must be less than regular price
        try:
            new_price = float(data['price'])
            new_discount = float(data['discount_price']) if data.get('discount_price') else None
            if new_discount is not None and new_discount >= new_price:
                return False, "Discount price must be less than the regular price.", None
            if new_price < 0:
                return False, "Price cannot be negative.", None
        except (ValueError, TypeError):
            return False, "Invalid price values.", None

        try:
            from datetime import datetime
            old_price = float(product.price)
            old_stock = product.stock_quantity
            # Always read the submitted stock (even if unchanged, to ensure it is written)
            new_stock = int(data.get('stock_quantity', 0))

            # ── Core field updates ──────────────────────────────────────────
            product.category_id = int(data['category_id'])
            product.name = data['name'].strip()
            product.sku = data['sku'].strip()
            product.brand = data['brand'].strip()
            product.model_number = data.get('model_number', '').strip()
            product.description = data.get('description', '').strip()
            product.specifications = data.get('specifications', '').strip()
            product.compatibility = data.get('compatibility', '').strip()
            product.price = new_price
            product.discount_price = new_discount
            product.minimum_stock_level = int(data.get('minimum_stock_level', 5))
            # Always assign stock_quantity regardless of change
            product.stock_quantity = new_stock
            if data.get('image'):
                product.image = data['image']
            product.status = data.get('status', 'active')
            # Force updated_at so next query sees a fresh timestamp
            product.updated_at = datetime.utcnow()

            # Log inventory transaction if stock actually changed
            if old_stock != new_stock:
                diff = new_stock - old_stock
                inv_trans = InventoryTransaction(
                    product_id=product.id,
                    transaction_type='Adjustment',
                    quantity=abs(diff),
                    previous_quantity=old_stock,
                    new_quantity=new_stock,
                    reference_type='Admin Edit',
                    notes=f"Stock manually updated by admin from {old_stock} to {new_stock}"
                )
                db.session.add(inv_trans)

            db.session.commit()

            # Expire the identity map so ANY subsequent query in this same process
            # re-reads from the database rather than the in-memory ORM cache.
            db.session.expire_all()

            log_audit(admin_id, 'UPDATE', 'Product', product.id,
                      f"Updated product {product.name}. Price: {old_price}->{new_price}, Stock: {old_stock}->{new_stock}")
            return True, "Product updated successfully!", product
        except Exception as e:
            db.session.rollback()
            return False, f"Failed to update product: {str(e)}", None

    @staticmethod
    def toggle_product_status(product_id, admin_id):
        product = db.session.get(Product, product_id)
        if not product:
            return False, "Product not found."

        new_status = 'inactive' if product.status == 'active' else 'active'
        product.status = new_status
        db.session.commit()
        log_audit(admin_id, 'TOGGLE_STATUS', 'Product', product.id, f"Product {product.name} status changed to {new_status}")
        return True, f"Product marked as {new_status}."

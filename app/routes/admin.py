import os
import uuid
import mimetypes
import time
from werkzeug.utils import secure_filename
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app, make_response
from flask_login import login_required, current_user
from app.utils.decorators import admin_required
from app import db
from app.models.product import Product
from app.models.category import Category
from app.models.user import User
from app.models.order import Order
from app.models.review import Review
from app.models.inventory import InventoryTransaction
from app.models.audit_log import AuditLog
from app.services.product_service import ProductService
from app.services.order_service import OrderService
from app.services.inventory_service import InventoryService
from app.analytics import SalesAnalytics, InventoryAnalytics, ProductAnalytics
from app.utils.helpers import log_audit

admin_bp = Blueprint('admin', __name__)

# Only allow safe, non-executable image formats
ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}

# Corresponding safe MIME types
ALLOWED_MIME_TYPES = {
    'image/jpeg', 'image/png', 'image/webp'
}

def allowed_image_file(filename):
    """Check file extension is in allowlist."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS

def validate_mime_type(file_storage):
    """Validate MIME type of uploaded file."""
    mime = mimetypes.guess_type(file_storage.filename)[0]
    if mime and mime in ALLOWED_MIME_TYPES:
        return True
    # If mimetypes can't guess, allow if extension is valid (fallback)
    return False

def save_uploaded_product_image(file_storage):
    """Save a valid uploaded product image and return the stored path.
    Saves to static/uploads/products/ with a UUID-based safe filename.
    Returns the relative path from static/ root, e.g. 'uploads/products/abc123.jpg'
    Returns None if validation fails.
    """
    if not file_storage or not file_storage.filename:
        return None
    
    if not allowed_image_file(file_storage.filename):
        return None
    
    # MIME type validation
    if not validate_mime_type(file_storage):
        # Fall back to extension-only check for safety
        ext = file_storage.filename.rsplit('.', 1)[1].lower()
        if ext not in ALLOWED_IMAGE_EXTENSIONS:
            return None
    
    ext = file_storage.filename.rsplit('.', 1)[1].lower()
    # Use UUID to prevent filename guessing and path traversal
    unique_filename = f"{uuid.uuid4().hex}.{ext}"
    
    target_dir = os.path.join(current_app.root_path, 'static', 'uploads', 'products')
    os.makedirs(target_dir, exist_ok=True)
    
    file_path = os.path.join(target_dir, unique_filename)
    file_storage.save(file_path)
    
    # Return relative path from static folder
    return f'uploads/products/{unique_filename}'

def delete_product_image_file(image_path):
    """Safely delete a product image file from disk.
    Only deletes files in the uploads/products/ directory (admin-uploaded files).
    Never deletes seeded/static product images.
    """
    if not image_path:
        return
    # Only delete files that are in the uploads directory (not seeded images)
    if not image_path.startswith('uploads/'):
        return
    abs_path = os.path.join(current_app.root_path, 'static', image_path)
    if os.path.isfile(abs_path):
        try:
            os.remove(abs_path)
        except OSError:
            pass  # Log silently, don't crash


@admin_bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
    total_customers = User.query.filter_by(role='customer').count()
    total_products = Product.query.count()
    total_orders = Order.query.count()
    
    orders = Order.query.filter(Order.order_status != 'Cancelled').all()
    total_revenue = sum(float(o.total_amount) for o in orders)
    pending_orders = Order.query.filter_by(order_status='Pending').count()

    low_stock_products = Product.query.filter(
        Product.stock_quantity > 0,
        Product.stock_quantity <= Product.minimum_stock_level
    ).all()
    out_of_stock_products = Product.query.filter(Product.stock_quantity <= 0).all()

    recent_orders = Order.query.order_by(Order.created_at.desc()).limit(5).all()

    # Analytics for charts
    sales_summary = SalesAnalytics.get_sales_summary()
    product_performance = ProductAnalytics.get_product_performance()

    return render_template(
        'admin/dashboard.html',
        total_customers=total_customers,
        total_products=total_products,
        total_orders=total_orders,
        total_revenue=total_revenue,
        pending_orders=pending_orders,
        low_stock_count=len(low_stock_products),
        out_of_stock_count=len(out_of_stock_products),
        low_stock_products=low_stock_products,
        out_of_stock_products=out_of_stock_products,
        recent_orders=recent_orders,
        sales_summary=sales_summary,
        product_performance=product_performance
    )


# ---------------- PRODUCT MANAGEMENT ----------------
@admin_bp.route('/products')
@login_required
@admin_required
def products():
    page = request.args.get('page', 1, type=int)
    q = request.args.get('q', '').strip()
    category_id = request.args.get('category', type=int)
    status = request.args.get('status', '').strip()

    query = Product.query
    if q:
        term = f"%{q}%"
        query = query.filter(Product.name.ilike(term) | Product.sku.ilike(term) | Product.brand.ilike(term))
    if category_id:
        query = query.filter(Product.category_id == category_id)
    if status:
        query = query.filter(Product.status == status)

    pagination = query.order_by(Product.updated_at.desc()).paginate(page=page, per_page=15, error_out=False)
    categories = Category.query.all()

    return render_template(
        'admin/products.html',
        pagination=pagination,
        products=pagination.items,
        categories=categories,
        current_q=q,
        current_category=category_id,
        current_status=status
    )


@admin_bp.route('/products/new', methods=['GET', 'POST'])
@login_required
@admin_required
def product_create():
    categories = Category.query.filter_by(status='active').all()

    if request.method == 'POST':
        data = request.form.to_dict()
        image_file = request.files.get('image_file')
        if image_file and image_file.filename:
            uploaded_path = save_uploaded_product_image(image_file)
            if uploaded_path:
                data['image'] = uploaded_path
            else:
                flash('Invalid image format. Only JPG, JPEG, PNG, and WEBP files are allowed.', 'warning')

        success, message, product = ProductService.create_product(data, current_user.id)
        if success:
            flash(message, 'success')
            return redirect(url_for('admin.products'))
        else:
            flash(message, 'danger')

    return render_template('admin/product_form.html', product=None, categories=categories)



@admin_bp.route('/products/edit/<int:product_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def product_edit(product_id):
    product = Product.query.get_or_404(product_id)
    categories = Category.query.all()

    if request.method == 'POST':
        data = request.form.to_dict()
        image_file = request.files.get('image_file')
        
        if image_file and image_file.filename:
            uploaded_path = save_uploaded_product_image(image_file)
            if uploaded_path:
                # Delete old image if it was admin-uploaded
                old_image = product.image
                data['image'] = uploaded_path
                delete_product_image_file(old_image)
            else:
                flash('Invalid image format. Only JPG, JPEG, PNG, and WEBP files are allowed.', 'warning')

        success, message, updated_product = ProductService.update_product(product_id, data, current_user.id)
        if success:
            flash(message, 'success')
            # Redirect with no-cache header so the browser always re-fetches
            # the product list (prevents back-button showing stale admin form)
            resp = make_response(redirect(url_for('admin.products')))
            resp.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate'
            return resp
        else:
            flash(message, 'danger')

    return render_template('admin/product_form.html', product=product, categories=categories)


@admin_bp.route('/products/remove-image/<int:product_id>', methods=['POST'])
@login_required
@admin_required
def product_remove_image(product_id):
    """Remove a product's image, leaving the product intact with a placeholder."""
    product = Product.query.get_or_404(product_id)
    old_image = product.image
    
    # Delete file if it was admin-uploaded
    delete_product_image_file(old_image)
    
    product.image = None
    db.session.commit()
    db.session.expire_all()  # Flush identity map after image removal
    log_audit(current_user.id, 'UPDATE', 'Product', product.id, f"Removed image from product {product.name}")
    flash(f"Image removed from '{product.name}'. A placeholder will be shown until a new image is uploaded.", 'info')
    resp = make_response(redirect(url_for('admin.product_edit', product_id=product_id)))
    resp.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate'
    return resp



@admin_bp.route('/products/toggle-status/<int:product_id>', methods=['POST'])
@login_required
@admin_required
def product_toggle_status(product_id):
    success, message = ProductService.toggle_product_status(product_id, current_user.id)
    flash(message, 'info')
    return redirect(url_for('admin.products'))


# ---------------- CATEGORY MANAGEMENT ----------------
@admin_bp.route('/categories', methods=['GET', 'POST'])
@login_required
@admin_required
def categories():
    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'add':
            name = request.form.get('name', '').strip()
            desc = request.form.get('description', '').strip()
            if not name:
                flash('Category name is required.', 'danger')
            elif Category.query.filter_by(name=name).first():
                flash('A category with this name already exists.', 'warning')
            else:
                cat = Category(name=name, description=desc, status='active')
                db.session.add(cat)
                db.session.commit()
                log_audit(current_user.id, 'CREATE', 'Category', cat.id, f"Created category '{name}'")
                flash(f"Category '{name}' created successfully!", 'success')

        elif action == 'edit':
            cat_id = request.form.get('category_id', type=int)
            name = request.form.get('name', '').strip()
            desc = request.form.get('description', '').strip()
            status = request.form.get('status', 'active')
            
            cat = Category.query.get_or_404(cat_id)
            cat.name = name
            cat.description = desc
            cat.status = status
            db.session.commit()
            log_audit(current_user.id, 'UPDATE', 'Category', cat.id, f"Updated category '{name}'")
            flash(f"Category '{name}' updated successfully!", 'success')

        return redirect(url_for('admin.categories'))

    categories_list = Category.query.order_by(Category.name.asc()).all()
    return render_template('admin/categories.html', categories=categories_list)


# ---------------- CUSTOMER MANAGEMENT ----------------
@admin_bp.route('/customers')
@login_required
@admin_required
def customers():
    page = request.args.get('page', 1, type=int)
    q = request.args.get('q', '').strip()

    query = User.query.filter_by(role='customer')
    if q:
        term = f"%{q}%"
        query = query.filter(User.name.ilike(term) | User.email.ilike(term) | User.phone.ilike(term))

    pagination = query.order_by(User.created_at.desc()).paginate(page=page, per_page=15, error_out=False)
    return render_template('admin/customers.html', pagination=pagination, customers=pagination.items, current_q=q)


@admin_bp.route('/customers/toggle-status/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def customer_toggle_status(user_id):
    user = User.query.get_or_404(user_id)
    if user.role == 'admin':
        flash('Cannot deactivate admin accounts.', 'danger')
        return redirect(url_for('admin.customers'))

    user.status = 'inactive' if user.status == 'active' else 'active'
    db.session.commit()
    log_audit(current_user.id, 'TOGGLE_STATUS', 'User', user.id, f"Customer {user.email} status changed to {user.status}")
    flash(f"Customer {user.name} is now {user.status}.", 'info')
    return redirect(url_for('admin.customers'))


# ---------------- ORDER MANAGEMENT ----------------
@admin_bp.route('/orders')
@login_required
@admin_required
def orders():
    page = request.args.get('page', 1, type=int)
    q = request.args.get('q', '').strip()
    status = request.args.get('status', '').strip()

    query = Order.query
    if q:
        term = f"%{q}%"
        query = query.filter(Order.order_number.ilike(term))
    if status:
        query = query.filter(Order.order_status == status)

    pagination = query.order_by(Order.created_at.desc()).paginate(page=page, per_page=15, error_out=False)
    return render_template('admin/orders.html', pagination=pagination, orders=pagination.items, current_q=q, current_status=status)


@admin_bp.route('/orders/update-status/<int:order_id>', methods=['POST'])
@login_required
@admin_required
def update_order_status(order_id):
    new_status = request.form.get('order_status')
    success, message = OrderService.update_order_status(order_id, new_status, current_user.id)
    if success:
        flash(message, 'success')
    else:
        flash(message, 'danger')
    return redirect(request.referrer or url_for('admin.orders'))


# ---------------- INVENTORY MANAGEMENT ----------------
@admin_bp.route('/inventory', methods=['GET', 'POST'])
@login_required
@admin_required
def inventory():
    if request.method == 'POST':
        product_id = request.form.get('product_id', type=int)
        new_quantity = request.form.get('new_quantity', type=int)
        trans_type = request.form.get('transaction_type', 'Adjustment')
        notes = request.form.get('notes', '').strip()

        success, message = InventoryService.adjust_stock(product_id, new_quantity, trans_type, notes, current_user.id)
        if success:
            flash(message, 'success')
        else:
            flash(message, 'danger')
        return redirect(url_for('admin.inventory'))

    products = Product.query.order_by(Product.name.asc()).all()
    recent_transactions = InventoryTransaction.query.order_by(InventoryTransaction.created_at.desc()).limit(20).all()
    inventory_summary = InventoryAnalytics.get_inventory_status()

    return render_template(
        'admin/inventory.html',
        products=products,
        transactions=recent_transactions,
        summary=inventory_summary
    )


# ---------------- REVIEWS MODERATION ----------------
@admin_bp.route('/reviews')
@login_required
@admin_required
def reviews():
    reviews_list = Review.query.order_by(Review.created_at.desc()).all()
    return render_template('admin/reviews.html', reviews=reviews_list)


@admin_bp.route('/reviews/delete/<int:review_id>', methods=['POST'])
@login_required
@admin_required
def delete_review(review_id):
    review = Review.query.get_or_404(review_id)
    db.session.delete(review)
    db.session.commit()
    log_audit(current_user.id, 'DELETE', 'Review', review_id, f"Deleted review #{review_id}")
    flash('Review deleted.', 'info')
    return redirect(url_for('admin.reviews'))

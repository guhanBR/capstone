from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app.utils.decorators import customer_required
from app import db
from app.models.order import Order
from app.models.address import Address
from app.models.product import Product
from app.models.review import Review
from app.models.notification import Notification
from app.models.wishlist import Wishlist
from app.models.cart import Cart, CartItem
from app.utils.validators import validate_phone

customer_bp = Blueprint('customer', __name__)


# ─────────────────────────────────────────────
# DASHBOARD
# ─────────────────────────────────────────────

@customer_bp.route('/dashboard')
@login_required
@customer_required
def dashboard():
    user_orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.created_at.desc()).all()

    total_orders = len(user_orders)
    pending_orders = len([o for o in user_orders if o.order_status in ['Pending', 'Confirmed', 'Processing', 'Packed', 'Shipped']])
    completed_orders = len([o for o in user_orders if o.order_status == 'Delivered'])
    total_spending = sum(float(o.total_amount) for o in user_orders if o.order_status != 'Cancelled')

    recent_orders = user_orders[:5]
    recommended_products = Product.query.filter_by(status='active').order_by(Product.stock_quantity.desc()).limit(4).all()

    return render_template(
        'customer/dashboard.html',
        total_orders=total_orders,
        pending_orders=pending_orders,
        completed_orders=completed_orders,
        total_spending=total_spending,
        recent_orders=recent_orders,
        recommended_products=recommended_products
    )


# ─────────────────────────────────────────────
# ACCOUNT / PROFILE (Profile + Settings + Addresses)
# ─────────────────────────────────────────────

@customer_bp.route('/profile', methods=['GET', 'POST'])
@login_required
@customer_required
def profile():
    # Determine which section to show
    active_section = request.args.get('section', 'profile')
    if active_section not in ('profile', 'settings', 'addresses'):
        active_section = 'profile'

    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'update_profile':
            name = request.form.get('name', '').strip()
            phone = request.form.get('phone', '').strip()
            valid_p, msg = validate_phone(phone)
            if not name:
                flash('Name cannot be empty.', 'danger')
            elif not valid_p:
                flash(msg, 'danger')
            else:
                current_user.name = name
                current_user.phone = phone
                db.session.commit()
                flash('Profile updated successfully!', 'success')
            return redirect(url_for('customer.profile', section='profile'))

        elif action == 'change_password':
            old_password = request.form.get('old_password', '')
            new_password = request.form.get('new_password', '')
            confirm_password = request.form.get('confirm_password', '')

            if not current_user.check_password(old_password):
                flash('Current password is incorrect.', 'danger')
            elif new_password != confirm_password:
                flash('New passwords do not match.', 'danger')
            elif len(new_password) < 6:
                flash('Password must be at least 6 characters long.', 'danger')
            else:
                current_user.set_password(new_password)
                db.session.commit()
                flash('Password changed successfully!', 'success')
            return redirect(url_for('customer.profile', section='settings'))

        elif action == 'add_address':
            full_name = request.form.get('full_name', '').strip()
            phone = request.form.get('phone', '').strip()
            address_line_1 = request.form.get('address_line_1', '').strip()
            address_line_2 = request.form.get('address_line_2', '').strip()
            city = request.form.get('city', '').strip()
            state = request.form.get('state', '').strip()
            postal_code = request.form.get('postal_code', '').strip()
            country = request.form.get('country', 'India').strip()
            is_default = True if request.form.get('is_default') else False

            if not all([full_name, phone, address_line_1, city, state, postal_code]):
                flash('Please fill in all required address fields.', 'danger')
                return redirect(url_for('customer.profile', section='addresses'))

            if is_default:
                Address.query.filter_by(user_id=current_user.id).update({'is_default': False})

            existing_count = Address.query.filter_by(user_id=current_user.id).count()
            addr = Address(
                user_id=current_user.id,
                full_name=full_name,
                phone=phone,
                address_line_1=address_line_1,
                address_line_2=address_line_2 or None,
                city=city,
                state=state,
                postal_code=postal_code,
                country=country,
                is_default=is_default or (existing_count == 0)
            )
            db.session.add(addr)
            db.session.commit()
            flash('Address added successfully!', 'success')
            return redirect(url_for('customer.profile', section='addresses'))

        elif action == 'edit_address':
            address_id = request.form.get('address_id', type=int)
            addr = db.session.get(Address, address_id)
            if not addr or addr.user_id != current_user.id:
                flash('Address not found.', 'danger')
                return redirect(url_for('customer.profile', section='addresses'))

            full_name = request.form.get('full_name', '').strip()
            phone = request.form.get('phone', '').strip()
            address_line_1 = request.form.get('address_line_1', '').strip()
            address_line_2 = request.form.get('address_line_2', '').strip()
            city = request.form.get('city', '').strip()
            state = request.form.get('state', '').strip()
            postal_code = request.form.get('postal_code', '').strip()
            country = request.form.get('country', 'India').strip()

            if not all([full_name, phone, address_line_1, city, state, postal_code]):
                flash('Please fill in all required address fields.', 'danger')
                return redirect(url_for('customer.profile', section='addresses'))

            addr.full_name = full_name
            addr.phone = phone
            addr.address_line_1 = address_line_1
            addr.address_line_2 = address_line_2 or None
            addr.city = city
            addr.state = state
            addr.postal_code = postal_code
            addr.country = country
            db.session.commit()
            flash('Address updated successfully!', 'success')
            return redirect(url_for('customer.profile', section='addresses'))

        return redirect(url_for('customer.profile', section=active_section))

    addresses = Address.query.filter_by(user_id=current_user.id).all()
    return render_template('customer/profile.html', addresses=addresses, active_section=active_section)


@customer_bp.route('/address/delete/<int:address_id>', methods=['POST'])
@login_required
@customer_required
def delete_address(address_id):
    addr = db.session.get(Address, address_id)
    if addr and addr.user_id == current_user.id:
        was_default = addr.is_default
        db.session.delete(addr)
        db.session.flush()
        # If deleted address was default, promote oldest remaining address
        if was_default:
            next_addr = Address.query.filter_by(user_id=current_user.id).order_by(Address.created_at).first()
            if next_addr:
                next_addr.is_default = True
        db.session.commit()
        flash('Address deleted.', 'info')
    else:
        flash('Address not found.', 'danger')
    return redirect(url_for('customer.profile', section='addresses'))


@customer_bp.route('/address/set-default/<int:address_id>', methods=['POST'])
@login_required
@customer_required
def set_default_address(address_id):
    addr = db.session.get(Address, address_id)
    if addr and addr.user_id == current_user.id:
        Address.query.filter_by(user_id=current_user.id).update({'is_default': False})
        addr.is_default = True
        db.session.commit()
        flash('Default address updated.', 'success')
    else:
        flash('Address not found.', 'danger')
    return redirect(url_for('customer.profile', section='addresses'))


# ─────────────────────────────────────────────
# WISHLIST
# ─────────────────────────────────────────────

@customer_bp.route('/wishlist')
@login_required
@customer_required
def wishlist():
    items = Wishlist.query.filter_by(user_id=current_user.id).order_by(Wishlist.created_at.desc()).all()
    return render_template('customer/wishlist.html', items=items)


@customer_bp.route('/wishlist/add/<int:product_id>', methods=['POST'])
@login_required
@customer_required
def wishlist_add(product_id):
    product = Product.query.filter_by(id=product_id, status='active').first()
    if not product:
        flash('Product not found.', 'danger')
        return redirect(request.referrer or url_for('products.list_products'))

    existing = Wishlist.query.filter_by(user_id=current_user.id, product_id=product_id).first()
    if existing:
        flash('This product is already in your wishlist.', 'info')
    else:
        item = Wishlist(user_id=current_user.id, product_id=product_id)
        db.session.add(item)
        db.session.commit()
        flash(f'"{product.name}" added to your wishlist!', 'success')

    return redirect(request.referrer or url_for('products.list_products'))


@customer_bp.route('/wishlist/remove/<int:wishlist_id>', methods=['POST'])
@login_required
@customer_required
def wishlist_remove(wishlist_id):
    item = db.session.get(Wishlist, wishlist_id)
    if item and item.user_id == current_user.id:
        db.session.delete(item)
        db.session.commit()
        flash('Item removed from wishlist.', 'info')
    else:
        flash('Wishlist item not found.', 'danger')
    return redirect(url_for('customer.wishlist'))


@customer_bp.route('/wishlist/to-cart/<int:product_id>', methods=['POST'])
@login_required
@customer_required
def wishlist_to_cart(product_id):
    product = Product.query.filter_by(id=product_id, status='active').first()
    if not product:
        flash('Product not found or no longer available.', 'danger')
        return redirect(url_for('customer.wishlist'))

    if product.stock_quantity <= 0:
        flash(f'"{product.name}" is currently out of stock and cannot be added to cart.', 'warning')
        return redirect(url_for('customer.wishlist'))

    cart = Cart.query.filter_by(user_id=current_user.id).first()
    if not cart:
        cart = Cart(user_id=current_user.id)
        db.session.add(cart)
        db.session.flush()

    cart_item = CartItem.query.filter_by(cart_id=cart.id, product_id=product_id).first()
    if cart_item:
        if cart_item.quantity + 1 > product.stock_quantity:
            flash(f'Only {product.stock_quantity} unit(s) available in stock.', 'warning')
            return redirect(url_for('customer.wishlist'))
        cart_item.quantity += 1
    else:
        cart_item = CartItem(cart_id=cart.id, product_id=product_id, quantity=1)
        db.session.add(cart_item)

    db.session.commit()
    flash(f'"{product.name}" added to cart successfully!', 'success')
    return redirect(url_for('customer.wishlist'))


# ─────────────────────────────────────────────
# NOTIFICATIONS
# ─────────────────────────────────────────────

@customer_bp.route('/notifications')
@login_required
@customer_required
def notifications():
    notifs = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.created_at.desc()).all()
    return render_template('customer/notifications.html', notifications=notifs)


@customer_bp.route('/notifications/mark-read/<int:notif_id>', methods=['POST'])
@login_required
@customer_required
def notification_mark_read(notif_id):
    notif = db.session.get(Notification, notif_id)
    if notif and notif.user_id == current_user.id:
        notif.is_read = True
        db.session.commit()
    return redirect(url_for('customer.notifications'))


@customer_bp.route('/notifications/mark-all-read', methods=['POST'])
@login_required
@customer_required
def notification_mark_all_read():
    Notification.query.filter_by(user_id=current_user.id, is_read=False).update({'is_read': True})
    db.session.commit()
    flash('All notifications marked as read.', 'success')
    return redirect(url_for('customer.notifications'))


# ─────────────────────────────────────────────
# MY REVIEWS
# ─────────────────────────────────────────────

@customer_bp.route('/reviews')
@login_required
@customer_required
def my_reviews():
    reviews = (
        Review.query
        .filter_by(user_id=current_user.id)
        .order_by(Review.created_at.desc())
        .all()
    )
    return render_template('customer/my_reviews.html', reviews=reviews)


@customer_bp.route('/reviews/edit/<int:review_id>', methods=['POST'])
@login_required
@customer_required
def edit_review(review_id):
    review = db.session.get(Review, review_id)
    if not review or review.user_id != current_user.id:
        flash('Review not found or access denied.', 'danger')
        return redirect(url_for('customer.my_reviews'))

    rating = request.form.get('rating', type=int)
    review_text = request.form.get('review_text', '').strip()

    if not rating or rating < 1 or rating > 5:
        flash('Please select a valid rating (1–5 stars).', 'danger')
        return redirect(url_for('customer.my_reviews'))

    review.rating = rating
    review.review_text = review_text
    db.session.commit()
    flash('Review updated successfully!', 'success')
    return redirect(url_for('customer.my_reviews'))


@customer_bp.route('/reviews/delete/<int:review_id>', methods=['POST'])
@login_required
@customer_required
def delete_review(review_id):
    review = db.session.get(Review, review_id)
    if not review or review.user_id != current_user.id:
        flash('Review not found or access denied.', 'danger')
        return redirect(url_for('customer.my_reviews'))

    db.session.delete(review)
    db.session.commit()
    flash('Review deleted.', 'info')
    return redirect(url_for('customer.my_reviews'))

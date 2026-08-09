from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app.utils.decorators import customer_required
from app import db
from app.models.cart import Cart, CartItem
from app.models.product import Product

cart_bp = Blueprint('cart', __name__)

@cart_bp.route('/')
@login_required
@customer_required
def view_cart():
    cart = Cart.query.filter_by(user_id=current_user.id).first()
    if not cart:
        cart = Cart(user_id=current_user.id)
        db.session.add(cart)
        db.session.commit()

    return render_template('customer/cart.html', cart=cart)


@cart_bp.route('/add', methods=['POST'])
@login_required
@customer_required
def add_to_cart():
    product_id = request.form.get('product_id', type=int)
    quantity = request.form.get('quantity', 1, type=int)

    if not product_id or quantity <= 0:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': 'Invalid product or quantity.'}), 400
        flash('Invalid product or quantity.', 'danger')
        return redirect(url_for('products.list_products'))

    product = Product.query.filter_by(id=product_id, status='active').first()
    if not product:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': 'Product not found.'}), 404
        flash('Product not found or is currently inactive.', 'danger')
        return redirect(url_for('products.list_products'))

    if product.stock_quantity <= 0:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': 'Product is currently out of stock.'}), 400
        flash('Product is currently out of stock.', 'warning')
        return redirect(url_for('products.product_detail', product_id=product.id))

    cart = Cart.query.filter_by(user_id=current_user.id).first()
    if not cart:
        cart = Cart(user_id=current_user.id)
        db.session.add(cart)
        db.session.flush()

    cart_item = CartItem.query.filter_by(cart_id=cart.id, product_id=product.id).first()
    new_qty = (cart_item.quantity if cart_item else 0) + quantity

    if new_qty > product.stock_quantity:
        msg = f"Cannot add {quantity} items. Only {product.stock_quantity} available in stock."
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'success': False, 'message': msg}), 400
        flash(msg, 'warning')
        return redirect(url_for('products.product_detail', product_id=product.id))

    if cart_item:
        cart_item.quantity = new_qty
    else:
        cart_item = CartItem(cart_id=cart.id, product_id=product.id, quantity=quantity)
        db.session.add(cart_item)

    db.session.commit()

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({
            'success': True,
            'message': f"'{product.name}' added to cart!",
            'cart_count': cart.total_items
        })

    flash(f"'{product.name}' added to your cart!", 'success')
    return redirect(url_for('cart.view_cart'))


@cart_bp.route('/update', methods=['POST'])
@login_required
@customer_required
def update_cart():
    item_id = request.form.get('item_id', type=int)
    quantity = request.form.get('quantity', type=int)

    if not item_id or quantity is None or quantity <= 0:
        flash('Invalid quantity.', 'danger')
        return redirect(url_for('cart.view_cart'))

    cart_item = CartItem.query.get_or_404(item_id)
    if cart_item.cart.user_id != current_user.id:
        flash('Unauthorized operation.', 'danger')
        return redirect(url_for('cart.view_cart'))

    product = cart_item.product
    if quantity > product.stock_quantity:
        flash(f"Cannot update quantity to {quantity}. Only {product.stock_quantity} in stock.", 'warning')
        return redirect(url_for('cart.view_cart'))

    cart_item.quantity = quantity
    db.session.commit()
    flash('Cart updated successfully.', 'success')
    return redirect(url_for('cart.view_cart'))


@cart_bp.route('/remove/<int:item_id>', methods=['POST'])
@login_required
@customer_required
def remove_item(item_id):
    cart_item = CartItem.query.get_or_404(item_id)
    if cart_item.cart.user_id == current_user.id:
        db.session.delete(cart_item)
        db.session.commit()
        flash('Item removed from cart.', 'info')
    return redirect(url_for('cart.view_cart'))


@cart_bp.route('/clear', methods=['POST'])
@login_required
@customer_required
def clear_cart():
    cart = Cart.query.filter_by(user_id=current_user.id).first()
    if cart:
        CartItem.query.filter_by(cart_id=cart.id).delete()
        db.session.commit()
        flash('Shopping cart cleared.', 'info')
    return redirect(url_for('cart.view_cart'))


@cart_bp.route('/buy-now', methods=['POST'])
def buy_now():
    from flask import session
    product_id = request.form.get('product_id', type=int)
    quantity = request.form.get('quantity', 1, type=int)

    if not product_id or quantity <= 0:
        flash('Invalid product selection or quantity.', 'danger')
        return redirect(url_for('products.list_products'))

    product = Product.query.filter_by(id=product_id, status='active').first()
    if not product:
        flash('This product is no longer available.', 'danger')
        return redirect(url_for('products.list_products'))

    if product.stock_quantity <= 0:
        flash(f"'{product.name}' is currently out of stock.", 'warning')
        return redirect(url_for('products.product_detail', product_id=product.id))

    if quantity > product.stock_quantity:
        flash(f"Only {product.stock_quantity} units are currently available. Please reduce the quantity.", 'warning')
        return redirect(url_for('products.product_detail', product_id=product.id))

    session['buy_now'] = {
        'product_id': product.id,
        'quantity': quantity
    }

    if not current_user.is_authenticated:
        flash('Please login to proceed with Buy Now checkout.', 'info')
        return redirect(url_for('auth.login', next=url_for('orders.checkout', mode='buy_now')))

    return redirect(url_for('orders.checkout', mode='buy_now'))


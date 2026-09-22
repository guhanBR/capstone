from flask import Blueprint, jsonify, request, make_response
from flask_login import current_user, login_required
from app import db
from app.models.product import Product
from app.models.category import Category
from app.models.cart import Cart, CartItem
from app.models.order import Order
from app.models.notification import Notification
from app.services.product_service import ProductService

api_bp = Blueprint('api', __name__)

@api_bp.route('/products', methods=['GET'])
def get_products():
    category_id = request.args.get('category_id', type=int)
    search = request.args.get('q', '')
    page = request.args.get('page', 1, type=int)

    # Expire identity map to ensure we read fresh data from DB
    db.session.expire_all()

    pagination = ProductService.get_products(
        category_id=category_id,
        search_query=search,
        status='active',
        page=page,
        per_page=12
    )

    resp = make_response(jsonify({
        'success': True,
        'data': [p.to_dict() for p in pagination.items],
        'total': pagination.total,
        'pages': pagination.pages,
        'current_page': pagination.page
    }))
    resp.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate'
    return resp


@api_bp.route('/products/<int:product_id>', methods=['GET'])
def get_product(product_id):
    # Expire identity map to ensure we read fresh data from DB
    db.session.expire_all()
    product = Product.query.filter_by(id=product_id, status='active').first()
    if not product:
        return jsonify({'success': False, 'message': 'Product not found'}), 404
    resp = make_response(jsonify({'success': True, 'data': product.to_dict()}))
    resp.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate'
    return resp


@api_bp.route('/categories', methods=['GET'])
def get_categories():
    categories = Category.query.filter_by(status='active').all()
    return jsonify({'success': True, 'data': [c.to_dict() for c in categories]})


@api_bp.route('/cart/add', methods=['POST'])
@login_required
def add_to_cart_api():
    data = request.get_json() or {}
    product_id = data.get('product_id')
    quantity = data.get('quantity', 1)

    if not product_id:
        return jsonify({'success': False, 'message': 'Product ID is required'}), 400

    product = Product.query.filter_by(id=product_id, status='active').first()
    if not product:
        return jsonify({'success': False, 'message': 'Product not found'}), 404

    if product.stock_quantity < quantity:
        return jsonify({'success': False, 'message': f'Insufficient stock. Only {product.stock_quantity} available.'}), 400

    cart = Cart.query.filter_by(user_id=current_user.id).first()
    if not cart:
        cart = Cart(user_id=current_user.id)
        db.session.add(cart)
        db.session.flush()

    item = CartItem.query.filter_by(cart_id=cart.id, product_id=product.id).first()
    if item:
        item.quantity += quantity
    else:
        item = CartItem(cart_id=cart.id, product_id=product.id, quantity=quantity)
        db.session.add(item)

    db.session.commit()
    return jsonify({'success': True, 'message': 'Product added to cart', 'cart_count': cart.total_items})


@api_bp.route('/cart/update', methods=['PUT'])
@login_required
def update_cart_api():
    data = request.get_json() or {}
    item_id = data.get('item_id')
    quantity = data.get('quantity')

    if not item_id or quantity is None or quantity <= 0:
        return jsonify({'success': False, 'message': 'Invalid input'}), 400

    item = CartItem.query.get(item_id)
    if not item or item.cart.user_id != current_user.id:
        return jsonify({'success': False, 'message': 'Cart item not found'}), 404

    if quantity > item.product.stock_quantity:
        return jsonify({'success': False, 'message': f'Cannot exceed available stock ({item.product.stock_quantity})'}), 400

    item.quantity = quantity
    db.session.commit()
    return jsonify({'success': True, 'message': 'Cart updated', 'subtotal': item.subtotal, 'cart_total': item.cart.subtotal})


@api_bp.route('/cart/remove/<int:item_id>', methods=['DELETE'])
@login_required
def remove_cart_item_api(item_id):
    item = CartItem.query.get(item_id)
    if item and item.cart.user_id == current_user.id:
        cart = item.cart
        db.session.delete(item)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Item removed', 'cart_count': cart.total_items})
    return jsonify({'success': False, 'message': 'Item not found'}), 404


@api_bp.route('/orders', methods=['GET'])
@login_required
def get_orders_api():
    if current_user.is_admin:
        orders = Order.query.order_by(Order.created_at.desc()).all()
    else:
        orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.created_at.desc()).all()
    return jsonify({'success': True, 'data': [o.to_dict() for o in orders]})


@api_bp.route('/notifications', methods=['GET'])
@login_required
def get_notifications_api():
    notifs = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.created_at.desc()).all()
    return jsonify({'success': True, 'data': [n.to_dict() for n in notifs]})


@api_bp.route('/notifications/<int:notif_id>/read', methods=['PUT'])
@login_required
def mark_notification_read_api(notif_id):
    notif = db.session.get(Notification, notif_id)
    if notif and notif.user_id == current_user.id:
        notif.is_read = True
        db.session.commit()
        return jsonify({'success': True, 'message': 'Notification marked as read'})
    return jsonify({'success': False, 'message': 'Notification not found'}), 404


@api_bp.route('/user/theme', methods=['POST'])
@login_required
def update_theme_preference():
    data = request.get_json() or {}
    theme = data.get('theme', 'dark')
    if theme in ['light', 'dark']:
        current_user.theme_preference = theme
        db.session.commit()
        return jsonify({'success': True, 'theme': theme})
    return jsonify({'success': False, 'message': 'Invalid theme'}), 400

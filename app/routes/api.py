from datetime import datetime, timezone
from flask import Blueprint, jsonify, request, make_response
from flask_login import current_user, login_required
from sqlalchemy import or_
from app import db
from app.models.product import Product
from app.models.category import Category
from app.models.cart import Cart, CartItem
from app.models.order import Order
from app.models.notification import Notification
from app.models.contact_message import ContactMessage
from app.models.contact_reply import ContactReply
from app.services.product_service import ProductService
from app.utils.decorators import manager_or_admin_required
from app.utils.email_helper import send_support_reply_email

api_bp = Blueprint('api', __name__)

VALID_SUPPORT_STATUSES = {'unread', 'read', 'replied', 'closed', 'in_progress'}


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

    item = db.session.get(CartItem, item_id)
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
    item = db.session.get(CartItem, item_id)
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
def update_theme_preference():
    data = request.get_json() or {}
    theme = data.get('theme', 'dark')
    if theme in ['light', 'dark']:
        if current_user.is_authenticated:
            current_user.theme_preference = theme
            db.session.commit()
        return jsonify({'success': True, 'theme': theme})
    return jsonify({'success': False, 'message': 'Invalid theme'}), 400


# ─────────────────────────────────────────────
# CUSTOMER SUPPORT MESSAGES API (ADMIN / MANAGER)
# ─────────────────────────────────────────────

@api_bp.route('/support-messages', methods=['GET'])
@manager_or_admin_required
def get_support_messages_api():
    status = request.args.get('status', '').strip().lower()
    search = request.args.get('q', '').strip()
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)

    # Force fresh DB read
    db.session.expire_all()

    query = ContactMessage.query

    if status and status in VALID_SUPPORT_STATUSES:
        query = query.filter(ContactMessage.status == status)

    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            or_(
                ContactMessage.name.ilike(search_pattern),
                ContactMessage.email.ilike(search_pattern),
                ContactMessage.phone.ilike(search_pattern),
                ContactMessage.subject.ilike(search_pattern),
                ContactMessage.message.ilike(search_pattern)
            )
        )

    pagination = query.order_by(ContactMessage.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    resp = make_response(jsonify({
        'success': True,
        'data': [m.to_dict() for m in pagination.items],
        'total': pagination.total,
        'pages': pagination.pages,
        'current_page': pagination.page,
        'per_page': per_page
    }))
    resp.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate'
    return resp


@api_bp.route('/support-messages/unread-count', methods=['GET'])
@manager_or_admin_required
def get_support_messages_unread_count_api():
    db.session.expire_all()
    count = ContactMessage.query.filter(
        or_(ContactMessage.is_read == False, ContactMessage.status == 'unread')
    ).count()
    resp = make_response(jsonify({'success': True, 'unread_count': count}))
    resp.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate'
    return resp


@api_bp.route('/support-messages/<int:message_id>', methods=['GET'])
@manager_or_admin_required
def get_support_message_detail_api(message_id):
    db.session.expire_all()
    message = db.session.get(ContactMessage, message_id)
    if not message:
        return jsonify({'success': False, 'message': 'Customer enquiry not found'}), 404

    # Mark as read when details are inspected
    if not message.is_read:
        message.is_read = True
        message.read_at = datetime.now(timezone.utc)
        if message.status == 'unread':
            message.status = 'read'
        db.session.commit()

    resp = make_response(jsonify({
        'success': True,
        'data': message.to_dict()
    }))
    resp.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate'
    return resp


@api_bp.route('/support-messages/<int:message_id>/read', methods=['POST', 'PUT'])
@manager_or_admin_required
def mark_support_message_read_api(message_id):
    message = db.session.get(ContactMessage, message_id)
    if not message:
        return jsonify({'success': False, 'message': 'Customer enquiry not found'}), 404

    if not message.is_read:
        message.is_read = True
        message.read_at = datetime.now(timezone.utc)
        if message.status == 'unread':
            message.status = 'read'
        db.session.commit()

    return jsonify({'success': True, 'message': 'Enquiry marked as read', 'data': message.to_dict()})



@api_bp.route('/support-messages/<int:message_id>/status', methods=['PUT', 'POST'])
@manager_or_admin_required
def update_support_message_status_api(message_id):
    message = db.session.get(ContactMessage, message_id)
    if not message:
        return jsonify({'success': False, 'message': 'Customer enquiry not found'}), 404

    data = request.get_json(silent=True) or {}
    new_status = (data.get('status') or request.form.get('status') or '').strip().lower()

    if not new_status or new_status not in VALID_SUPPORT_STATUSES:
        return jsonify({
            'success': False,
            'message': f"Invalid status value. Supported values: {', '.join(sorted(VALID_SUPPORT_STATUSES))}"
        }), 400

    message.status = new_status
    db.session.commit()

    return jsonify({
        'success': True,
        'message': f'Status updated to {new_status}',
        'data': message.to_dict()
    })


@api_bp.route('/support-messages/<int:message_id>/replies', methods=['GET'])
@manager_or_admin_required
def get_support_message_replies_api(message_id):
    message = db.session.get(ContactMessage, message_id)
    if not message:
        return jsonify({'success': False, 'message': 'Customer enquiry not found'}), 404

    replies = ContactReply.query.filter_by(contact_message_id=message_id).order_by(ContactReply.created_at.asc()).all()
    return jsonify({
        'success': True,
        'data': [r.to_dict() for r in replies]
    })


@api_bp.route('/support-messages/<int:message_id>/reply', methods=['POST'])
@manager_or_admin_required
def post_support_message_reply_api(message_id):
    message = db.session.get(ContactMessage, message_id)
    if not message:
        return jsonify({'success': False, 'message': 'Customer enquiry not found'}), 404

    data = request.get_json(silent=True) or {}
    subject = (data.get('subject') or request.form.get('subject') or '').strip()
    reply_body = (data.get('reply_body') or request.form.get('reply_body') or '').strip()

    if not subject or not reply_body:
        return jsonify({'success': False, 'message': 'Subject and reply body are required.'}), 400

    recipient_email = message.email.strip()

    # Step 1: Create ContactReply record in Pending state and commit DB first (non-blocking)
    reply = ContactReply(
        contact_message_id=message.id,
        staff_id=current_user.id if hasattr(current_user, 'id') else None,
        recipient_email=recipient_email,
        subject=subject,
        reply_body=reply_body,
        sending_status='Pending'
    )
    db.session.add(reply)
    db.session.commit()

    reply_id = reply.id

    # Step 2: Perform SMTP email sending outside of open DB transaction
    success, email_msg, provider_msg_id = send_support_reply_email(recipient_email, subject, reply_body)

    # Step 3: Open fresh DB update to record final sending status
    reply_rec = db.session.get(ContactReply, reply_id)
    if reply_rec:
        if success:
            reply_rec.sending_status = 'Sent'
            reply_rec.provider_message_id = provider_msg_id
            # Also update original message status to replied
            msg_rec = db.session.get(ContactMessage, message.id)
            if msg_rec:
                msg_rec.status = 'replied'
            db.session.commit()
            return jsonify({
                'success': True,
                'message': 'Reply sent successfully and recorded in history.',
                'data': reply_rec.to_dict()
            })
        else:
            reply_rec.sending_status = 'Failed'
            reply_rec.error_message = email_msg
            db.session.commit()
            return jsonify({
                'success': False,
                'message': email_msg,
                'data': reply_rec.to_dict()
            }), 400

    return jsonify({'success': False, 'message': 'Failed to process reply.'}), 500



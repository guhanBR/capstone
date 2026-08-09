import uuid
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.utils.decorators import customer_required
from app.services.order_service import OrderService
from app.models.cart import Cart
from app.models.address import Address
from app.models.order import Order

orders_bp = Blueprint('orders', __name__)

@orders_bp.route('/checkout', methods=['GET', 'POST'])
@login_required
@customer_required
def checkout():
    from flask import session
    from app.models.product import Product

    mode = request.args.get('mode') or request.form.get('mode')
    buy_now_data = session.get('buy_now')

    # is_buy_now is True when mode=buy_now is present AND we have session data
    is_buy_now = (mode == 'buy_now') and bool(buy_now_data)

    if is_buy_now:
        product_id = buy_now_data.get('product_id')
        quantity = buy_now_data.get('quantity', 1)

        product = Product.query.filter_by(id=product_id, status='active').first()
        if not product:
            session.pop('buy_now', None)
            flash('This product is no longer available.', 'danger')
            return redirect(url_for('products.list_products'))

        if product.stock_quantity <= 0:
            session.pop('buy_now', None)
            flash('This product is currently out of stock.', 'warning')
            return redirect(url_for('products.product_detail', product_id=product.id))

        if quantity > product.stock_quantity:
            flash(f"Only {product.stock_quantity} units are currently available. Please reduce the quantity.", 'warning')
            quantity = product.stock_quantity
            buy_now_data['quantity'] = quantity
            session['buy_now'] = buy_now_data

        subtotal = product.effective_price * quantity
        buy_now_cart = {
            'is_buy_now': True,
            'product': product,
            'quantity': quantity,
            'subtotal': subtotal,
            'total_items': quantity,
            'items': [{
                'product': product,
                'quantity': quantity,
                'unit_price': product.effective_price,
                'subtotal': subtotal
            }]
        }

        addresses = Address.query.filter_by(user_id=current_user.id).all()

        if request.method == 'POST':
            address_id = request.form.get('address_id', type=int)
            payment_method = request.form.get('payment_method', 'Cash on Delivery')

            # --- Duplicate order prevention (nonce check) ---
            submitted_nonce = request.form.get('checkout_nonce')
            session_nonce = session.get('checkout_nonce')
            if not submitted_nonce or submitted_nonce != session_nonce:
                flash('This order has already been submitted or the page was refreshed. Please start again.', 'warning')
                return redirect(url_for('orders.checkout', mode='buy_now'))
            # Consume nonce immediately
            session.pop('checkout_nonce', None)

            if not address_id and request.form.get('full_name'):
                full_name = request.form.get('full_name')
                phone = request.form.get('phone')
                line1 = request.form.get('address_line_1')
                line2 = request.form.get('address_line_2')
                city = request.form.get('city')
                state = request.form.get('state')
                postal_code = request.form.get('postal_code')
                country = request.form.get('country', 'India')

                from app import db
                new_addr = Address(
                    user_id=current_user.id,
                    full_name=full_name,
                    phone=phone,
                    address_line_1=line1,
                    address_line_2=line2,
                    city=city,
                    state=state,
                    postal_code=postal_code,
                    country=country,
                    is_default=(len(addresses) == 0)
                )
                db.session.add(new_addr)
                db.session.commit()
                address_id = new_addr.id

            if not address_id:
                # Regenerate nonce so customer can try again
                new_nonce = str(uuid.uuid4())
                session['checkout_nonce'] = new_nonce
                flash('Please select or add a shipping address.', 'danger')
                return render_template('customer/checkout.html', cart=buy_now_cart, addresses=addresses, is_buy_now=True, checkout_nonce=new_nonce)

            success, message, order = OrderService.create_buy_now_order(
                user_id=current_user.id,
                address_id=address_id,
                product_id=product.id,
                quantity=quantity,
                payment_method=payment_method
            )

            if success:
                session.pop('buy_now', None)
                return redirect(url_for('orders.order_detail', order_number=order.order_number, confirmed=1))
            else:
                # Regenerate nonce so customer can try again
                new_nonce = str(uuid.uuid4())
                session['checkout_nonce'] = new_nonce
                flash(message, 'danger')
                return render_template('customer/checkout.html', cart=buy_now_cart, addresses=addresses, is_buy_now=True, checkout_nonce=new_nonce)

        # GET — issue a fresh nonce
        nonce = str(uuid.uuid4())
        session['checkout_nonce'] = nonce
        return render_template('customer/checkout.html', cart=buy_now_cart, addresses=addresses, is_buy_now=True, checkout_nonce=nonce)

    # Normal cart checkout
    cart = Cart.query.filter_by(user_id=current_user.id).first()
    if not cart or not cart.items:
        flash('Your cart is empty. Add products before checking out.', 'warning')
        return redirect(url_for('products.list_products'))

    addresses = Address.query.filter_by(user_id=current_user.id).all()

    if request.method == 'POST':
        address_id = request.form.get('address_id', type=int)
        payment_method = request.form.get('payment_method', 'Cash on Delivery')

        # --- Duplicate order prevention (nonce check) ---
        submitted_nonce = request.form.get('checkout_nonce')
        session_nonce = session.get('checkout_nonce')
        if not submitted_nonce or submitted_nonce != session_nonce:
            flash('This order has already been submitted or the page was refreshed. Please start again.', 'warning')
            return redirect(url_for('orders.checkout'))
        # Consume nonce immediately
        session.pop('checkout_nonce', None)

        if not address_id and request.form.get('full_name'):
            full_name = request.form.get('full_name')
            phone = request.form.get('phone')
            line1 = request.form.get('address_line_1')
            line2 = request.form.get('address_line_2')
            city = request.form.get('city')
            state = request.form.get('state')
            postal_code = request.form.get('postal_code')
            country = request.form.get('country', 'India')

            from app import db
            new_addr = Address(
                user_id=current_user.id,
                full_name=full_name,
                phone=phone,
                address_line_1=line1,
                address_line_2=line2,
                city=city,
                state=state,
                postal_code=postal_code,
                country=country,
                is_default=(len(addresses) == 0)
            )
            db.session.add(new_addr)
            db.session.commit()
            address_id = new_addr.id

        if not address_id:
            # Regenerate nonce so customer can try again
            new_nonce = str(uuid.uuid4())
            session['checkout_nonce'] = new_nonce
            flash('Please select or add a shipping address.', 'danger')
            return render_template('customer/checkout.html', cart=cart, addresses=addresses, is_buy_now=False, checkout_nonce=new_nonce)

        success, message, order = OrderService.create_order(
            user_id=current_user.id,
            address_id=address_id,
            payment_method=payment_method
        )

        if success:
            return redirect(url_for('orders.order_detail', order_number=order.order_number, confirmed=1))
        else:
            # Regenerate nonce so customer can try again
            new_nonce = str(uuid.uuid4())
            session['checkout_nonce'] = new_nonce
            flash(message, 'danger')
            return render_template('customer/checkout.html', cart=cart, addresses=addresses, is_buy_now=False, checkout_nonce=new_nonce)

    # GET — issue a fresh nonce
    nonce = str(uuid.uuid4())
    session['checkout_nonce'] = nonce
    return render_template('customer/checkout.html', cart=cart, addresses=addresses, is_buy_now=False, checkout_nonce=nonce)


@orders_bp.route('/')
@login_required
@customer_required
def order_history():
    orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.created_at.desc()).all()
    return render_template('customer/orders.html', orders=orders)


@orders_bp.route('/<order_number>')
@login_required
def order_detail(order_number):
    order = Order.query.filter_by(order_number=order_number).first_or_404()
    
    # Customer can only view their own orders unless admin
    if not current_user.is_admin and order.user_id != current_user.id:
        flash('Unauthorized to view this order.', 'danger')
        return redirect(url_for('orders.order_history'))

    # Visual tracking timeline steps
    timeline_steps = [
        {'name': 'Placed', 'key': 'Pending'},
        {'name': 'Confirmed', 'key': 'Confirmed'},
        {'name': 'Processing', 'key': 'Processing'},
        {'name': 'Packed', 'key': 'Packed'},
        {'name': 'Shipped', 'key': 'Shipped'},
        {'name': 'Delivered', 'key': 'Delivered'}
    ]

    # Calculate status index for progress bar
    status_order = ['Pending', 'Confirmed', 'Processing', 'Packed', 'Shipped', 'Delivered']
    current_index = status_order.index(order.order_status) if order.order_status in status_order else -1

    return render_template(
        'customer/order_detail.html',
        order=order,
        timeline_steps=timeline_steps,
        current_index=current_index
    )

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
    cart = Cart.query.filter_by(user_id=current_user.id).first()
    if not cart or not cart.items:
        flash('Your cart is empty. Add products before checking out.', 'warning')
        return redirect(url_for('products.list_products'))

    addresses = Address.query.filter_by(user_id=current_user.id).all()

    if request.method == 'POST':
        address_id = request.form.get('address_id', type=int)
        payment_method = request.form.get('payment_method', 'Cash on Delivery')

        # If user submitted a new inline address
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
            flash('Please select or add a shipping address.', 'danger')
            return render_template('customer/checkout.html', cart=cart, addresses=addresses)

        success, message, order = OrderService.create_order(
            user_id=current_user.id,
            address_id=address_id,
            payment_method=payment_method
        )

        if success:
            flash(message, 'success')
            return redirect(url_for('orders.order_detail', order_number=order.order_number))
        else:
            flash(message, 'danger')
            return render_template('customer/checkout.html', cart=cart, addresses=addresses)

    return render_template('customer/checkout.html', cart=cart, addresses=addresses)


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

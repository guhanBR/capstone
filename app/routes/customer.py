from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app.utils.decorators import customer_required
from app import db
from app.models.order import Order
from app.models.address import Address
from app.models.product import Product
from app.utils.validators import validate_phone

customer_bp = Blueprint('customer', __name__)

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


@customer_bp.route('/profile', methods=['GET', 'POST'])
@login_required
@customer_required
def profile():
    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'update_profile':
            name = request.form.get('name')
            phone = request.form.get('phone')
            valid_p, msg = validate_phone(phone)
            if not valid_p:
                flash(msg, 'danger')
            else:
                current_user.name = name.strip()
                current_user.phone = phone.strip()
                db.session.commit()
                flash('Profile updated successfully!', 'success')

        elif action == 'change_password':
            old_password = request.form.get('old_password')
            new_password = request.form.get('new_password')
            confirm_password = request.form.get('confirm_password')

            if not current_user.check_password(old_password):
                flash('Incorrect current password.', 'danger')
            elif new_password != confirm_password:
                flash('New passwords do not match.', 'danger')
            elif len(new_password) < 6:
                flash('Password must be at least 6 characters long.', 'danger')
            else:
                current_user.set_password(new_password)
                db.session.commit()
                flash('Password changed successfully!', 'success')

        elif action == 'add_address':
            full_name = request.form.get('full_name')
            phone = request.form.get('phone')
            address_line_1 = request.form.get('address_line_1')
            address_line_2 = request.form.get('address_line_2')
            city = request.form.get('city')
            state = request.form.get('state')
            postal_code = request.form.get('postal_code')
            country = request.form.get('country', 'India')
            is_default = True if request.form.get('is_default') else False

            if is_default:
                Address.query.filter_by(user_id=current_user.id).update({'is_default': False})

            addr = Address(
                user_id=current_user.id,
                full_name=full_name,
                phone=phone,
                address_line_1=address_line_1,
                address_line_2=address_line_2,
                city=city,
                state=state,
                postal_code=postal_code,
                country=country,
                is_default=is_default or (Address.query.filter_by(user_id=current_user.id).count() == 0)
            )
            db.session.add(addr)
            db.session.commit()
            flash('Address added successfully!', 'success')

        return redirect(url_for('customer.profile'))

    addresses = Address.query.filter_by(user_id=current_user.id).all()
    return render_template('customer/profile.html', addresses=addresses)


@customer_bp.route('/address/delete/<int:address_id>', methods=['POST'])
@login_required
@customer_required
def delete_address(address_id):
    addr = db.session.get(Address, address_id)
    if addr and addr.user_id == current_user.id:
        db.session.delete(addr)
        db.session.commit()
        flash('Address deleted.', 'info')
    return redirect(url_for('customer.profile'))

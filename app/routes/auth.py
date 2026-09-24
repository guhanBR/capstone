from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from app.services.auth_service import AuthService
from app import db

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        if current_user.is_staff:
            return redirect(url_for('admin.dashboard'))
        return redirect(url_for('customer.dashboard'))

    if request.method == 'POST':
        from flask import session
        email = request.form.get('email')
        password = request.form.get('password')
        remember = True if request.form.get('remember') else False

        success, message, user = AuthService.authenticate_user(email, password)
        if success:
            login_user(user, remember=remember)
            flash(message, 'success')
            next_page = request.args.get('next')
            # If buy_now session is active, always go to buy_now checkout after login
            if session.get('buy_now'):
                return redirect(url_for('orders.checkout', mode='buy_now'))
            if next_page:
                return redirect(next_page)
            if user.is_staff:
                return redirect(url_for('admin.dashboard'))
            return redirect(url_for('customer.dashboard'))
        else:
            flash(message, 'danger')

    return render_template('auth/login.html')


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('customer.dashboard'))

    if request.method == 'POST':
        from flask import session
        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return render_template('auth/register.html')

        success, message, user = AuthService.register_user(name, email, phone, password, role='customer')
        if success:
            login_user(user)
            flash('Registration successful! Welcome to SparePro.', 'success')
            # If buy_now session is active, go to buy_now checkout after registration
            if session.get('buy_now'):
                return redirect(url_for('orders.checkout', mode='buy_now'))
            return redirect(url_for('customer.dashboard'))
        else:
            flash(message, 'danger')

    return render_template('auth/register.html')



@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))


@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email')
        flash('If an account exists with this email, password reset instructions have been sent.', 'info')
        return redirect(url_for('auth.login'))
    return render_template('auth/forgot_password.html')

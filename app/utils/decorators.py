from functools import wraps
from flask import abort, flash, redirect, url_for, jsonify, request
from flask_login import current_user

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            if request.path.startswith('/api/'):
                return jsonify({'success': False, 'message': 'Authentication required'}), 401
            flash('Please log in to access the admin area.', 'warning')
            return redirect(url_for('auth.login', next=request.url))
        if not current_user.is_admin:
            if request.path.startswith('/api/'):
                return jsonify({'success': False, 'message': 'Admin privileges required'}), 403
            abort(403)
        return f(*args, **kwargs)
    return decorated_function

def customer_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            if request.path.startswith('/api/'):
                return jsonify({'success': False, 'message': 'Authentication required'}), 401
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.login', next=request.url))
        if current_user.is_admin:
            flash('Admins cannot perform customer operations.', 'info')
            return redirect(url_for('admin.dashboard'))
        return f(*args, **kwargs)
    return decorated_function

from functools import wraps
from flask import abort, flash, redirect, url_for, jsonify, request
from flask_login import current_user

def admin_required(f):
    """Restricts access to Owner / Admin accounts only."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            if request.path.startswith('/api/'):
                return jsonify({'success': False, 'message': 'Authentication required'}), 401
            flash('Please log in to access the admin area.', 'warning')
            return redirect(url_for('auth.login', next=request.url))
        if not current_user.is_admin:
            if request.path.startswith('/api/'):
                return jsonify({'success': False, 'message': 'Owner/Admin privileges required'}), 403
            abort(403)
        return f(*args, **kwargs)
    return decorated_function

def manager_or_admin_required(f):
    """Restricts access to Owner/Admin and Manager accounts."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            if request.path.startswith('/api/'):
                return jsonify({'success': False, 'message': 'Authentication required'}), 401
            flash('Please log in to access the admin area.', 'warning')
            return redirect(url_for('auth.login', next=request.url))
        if current_user.role not in ('admin', 'manager'):
            if request.path.startswith('/api/'):
                return jsonify({'success': False, 'message': 'Manager or Admin privileges required'}), 403
            abort(403)
        return f(*args, **kwargs)
    return decorated_function

def staff_required(f):
    """Restricts access to any authorized staff account (Admin, Manager, Employee)."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            if request.path.startswith('/api/'):
                return jsonify({'success': False, 'message': 'Authentication required'}), 401
            flash('Please log in to access the admin area.', 'warning')
            return redirect(url_for('auth.login', next=request.url))
        if not current_user.is_staff:
            if request.path.startswith('/api/'):
                return jsonify({'success': False, 'message': 'Staff privileges required'}), 403
            abort(403)
        return f(*args, **kwargs)
    return decorated_function

def customer_required(f):
    """Restricts access to customer accounts only. Staff are redirected to admin dashboard."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            if request.path.startswith('/api/'):
                return jsonify({'success': False, 'message': 'Authentication required'}), 401
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('auth.login', next=request.url))
        if current_user.is_staff:
            flash('Staff members cannot perform customer operations.', 'info')
            return redirect(url_for('admin.dashboard'))
        return f(*args, **kwargs)
    return decorated_function

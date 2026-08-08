import os
from flask import Flask, render_template, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from config import config

db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()

login_manager.login_view = 'auth.login'
login_manager.login_message_category = 'warning'
login_manager.login_message = 'Please log in to access this page.'

def create_app(config_name=None):
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')

    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config[config_name])

    # Try database connection; fallback to SQLite if MySQL is unreachable during dev
    db_uri = app.config['SQLALCHEMY_DATABASE_URI']
    if 'mysql' in db_uri:
        try:
            import pymysql
            host = app.config.get('MYSQL_HOST', 'localhost')
            port = app.config.get('MYSQL_PORT', 3306)
            user = app.config.get('MYSQL_USER', 'root')
            password = app.config.get('MYSQL_PASSWORD', 'rootpassword')
            # Test direct connection
            conn = pymysql.connect(host=host, port=port, user=user, password=password, connect_timeout=2)
            conn.close()
        except Exception as e:
            # Fallback to SQLite if local MySQL daemon isn't running
            print(f"[Warning] MySQL connection test failed ({e}). Falling back to SQLite database.")
            app.config['SQLALCHEMY_DATABASE_URI'] = app.config['FALLBACK_SQLITE_URI']

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    # User loader for Flask-Login
    from app.models.user import User

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    # Register Blueprints
    from app.routes.auth import auth_bp
    from app.routes.customer import customer_bp
    from app.routes.products import products_bp
    from app.routes.cart import cart_bp
    from app.routes.orders import orders_bp
    from app.routes.reviews import reviews_bp
    from app.routes.admin import admin_bp
    from app.routes.reports import reports_bp
    from app.routes.api import api_bp

    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(customer_bp, url_prefix='/customer')
    app.register_blueprint(products_bp, url_prefix='/products')
    app.register_blueprint(cart_bp, url_prefix='/cart')
    app.register_blueprint(orders_bp, url_prefix='/orders')
    app.register_blueprint(reviews_bp, url_prefix='/reviews')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(reports_bp, url_prefix='/reports')
    app.register_blueprint(api_bp, url_prefix='/api')

    # Main index route
    @app.route('/')
    def index():
        from flask import redirect, url_for
        return redirect(url_for('products.list_products'))

    # Custom Error Handlers
    @app.errorhandler(400)
    def bad_request_error(error):
        if app.config.get('TESTING'):
            return jsonify({'success': False, 'message': 'Bad Request'}), 400
        return render_template('errors/400.html'), 400

    @app.errorhandler(403)
    def forbidden_error(error):
        if app.config.get('TESTING'):
            return jsonify({'success': False, 'message': 'Forbidden'}), 403
        return render_template('errors/403.html'), 403

    @app.errorhandler(404)
    def not_found_error(error):
        if app.config.get('TESTING'):
            return jsonify({'success': False, 'message': 'Not Found'}), 404
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        if app.config.get('TESTING'):
            return jsonify({'success': False, 'message': 'Internal Server Error'}), 500
        return render_template('errors/500.html'), 500

    # Inject global context variables (e.g. cart count, categories)
    @app.context_processor
    def inject_globals():
        from flask_login import current_user
        from app.models.category import Category
        from app.models.notification import Notification

        cart_count = 0
        unread_notifications = 0
        if current_user.is_authenticated:
            if current_user.cart:
                cart_count = current_user.cart.total_items
            unread_notifications = Notification.query.filter_by(user_id=current_user.id, is_read=False).count()

        categories = Category.query.filter_by(status='active').all()
        return dict(
            categories=categories,
            cart_count=cart_count,
            unread_notifications=unread_notifications
        )

    # Ensure upload directory exists
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    with app.app_context():
        db.create_all()

    return app

from flask import Blueprint, render_template, request, current_app, make_response
from app.services.product_service import ProductService
from app.models.product import Product
from app.models.category import Category
from app.models.review import Review

products_bp = Blueprint('products', __name__)

@products_bp.route('/')
def list_products():
    page = request.args.get('page', 1, type=int)
    search_query = request.args.get('q', '').strip()
    category_id = request.args.get('category', type=int)
    brand = request.args.get('brand', '').strip()
    min_price = request.args.get('min_price', type=float)
    max_price = request.args.get('max_price', type=float)
    availability = request.args.get('availability', '').strip()
    sort_by = request.args.get('sort', 'newest').strip()

    per_page = current_app.config['ITEMS_PER_PAGE']
    max_db_price = ProductService.get_max_price()

    pagination = ProductService.get_products(
        category_id=category_id,
        brand=brand if brand else None,
        min_price=min_price,
        max_price=max_price,
        availability=availability if availability else None,
        search_query=search_query if search_query else None,
        sort_by=sort_by,
        status='active',
        page=page,
        per_page=per_page
    )

    categories = Category.query.filter_by(status='active').all()
    brands = ProductService.get_brands()

    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.args.get('ajax') == '1'

    template_name = 'customer/_product_grid.html' if is_ajax else 'customer/products.html'

    rendered = render_template(
        template_name,
        pagination=pagination,
        products=pagination.items,
        categories=categories,
        brands=brands,
        current_category=category_id,
        current_brand=brand,
        current_search=search_query,
        current_sort=sort_by,
        current_min_price=min_price,
        current_max_price=max_price,
        current_availability=availability,
        max_db_price=max_db_price
    )
    resp = make_response(rendered)
    # Ensure browsers always re-fetch product data from the server
    # so admin changes (price, stock, image, etc.) are immediately visible
    resp.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate'
    resp.headers['Pragma'] = 'no-cache'
    return resp


@products_bp.route('/<int:product_id>')
def product_detail(product_id):
    product = Product.query.filter_by(id=product_id, status='active').first_or_404()
    
    # Related products from same category or brand
    related_products = Product.query.filter(
        Product.category_id == product.category_id,
        Product.id != product.id,
        Product.status == 'active'
    ).limit(4).all()

    # Approved reviews
    reviews = Review.query.filter_by(product_id=product.id, status='approved').order_by(Review.created_at.desc()).all()

    rendered = render_template(
        'customer/product_detail.html',
        product=product,
        related_products=related_products,
        reviews=reviews
    )
    resp = make_response(rendered)
    # Force browser to re-fetch product detail every time so admin changes
    # (price, stock, description, image) are immediately visible on next load
    resp.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate'
    resp.headers['Pragma'] = 'no-cache'
    return resp

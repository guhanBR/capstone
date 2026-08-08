import pytest
from app import create_app, db
from app.models.user import User
from app.models.category import Category
from app.models.product import Product
from app.models.cart import Cart, CartItem

@pytest.fixture
def app_context():
    app = create_app('testing')
    with app.app_context():
        db.create_all()
        user = User(name="Cart User", email="cart@example.com", phone="9876543210")
        user.set_password("pass123")
        db.session.add(user)
        db.session.flush()

        cat = Category(name="Bearings")
        db.session.add(cat)
        db.session.flush()

        p = Product(category_id=cat.id, name="6203 Bearing", sku="6203", brand="SKF", price=150, stock_quantity=10, description="D")
        db.session.add(p)

        cart = Cart(user_id=user.id)
        db.session.add(cart)
        db.session.commit()

        yield app

def test_add_to_cart(app_context):
    client = app_context.test_client()
    client.post('/auth/login', data={'email': 'cart@example.com', 'password': 'pass123'})

    res = client.post('/cart/add', data={'product_id': 1, 'quantity': 2}, follow_redirects=True)
    assert res.status_code == 200

    with app_context.app_context():
        cart = Cart.query.filter_by(user_id=1).first()
        assert cart.total_items == 2
        assert float(cart.subtotal) == 300.0

def test_cart_exceed_stock_validation(app_context):
    client = app_context.test_client()
    client.post('/auth/login', data={'email': 'cart@example.com', 'password': 'pass123'})

    # Try adding 15 when only 10 in stock
    res = client.post('/cart/add', data={'product_id': 1, 'quantity': 15}, follow_redirects=True)
    assert b'Only 10 available in stock' in res.data

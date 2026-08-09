"""
Tests for Buy Now Quick Purchase Flow.
Tests verify that:
 - Buy Now sets session correctly and redirects to checkout
 - Existing cart items remain unchanged after Buy Now purchase
 - Stock validation rejects over-quantity requests
 - Unauthenticated users are redirected to login with session intact
 - Server-side price calculation is used (not client-supplied)
"""
import pytest
from flask import session
from app import create_app, db
from app.models.user import User
from app.models.category import Category
from app.models.product import Product
from app.models.cart import Cart, CartItem
from app.models.address import Address
from app.models.order import Order


@pytest.fixture
def app_context():
    app = create_app('testing')
    with app.app_context():
        db.create_all()

        # Create a customer user
        user = User(name="Buy Now User", email="buynow@example.com", phone="9876543211")
        user.set_password("pass123")
        db.session.add(user)
        db.session.flush()

        # Create category
        cat = Category(name="Bearings", status="active")
        db.session.add(cat)
        db.session.flush()

        # Create products
        p1 = Product(
            category_id=cat.id, name="6203 Bearing", sku="BRG-6203",
            brand="SKF", price=450, stock_quantity=10,
            description="Deep Groove Ball Bearing", status="active"
        )
        p2 = Product(
            category_id=cat.id, name="Mechanical Seal", sku="SEAL-25",
            brand="Burgmann", price=700, stock_quantity=5,
            description="25mm mechanical seal", status="active"
        )
        p_oos = Product(
            category_id=cat.id, name="Out of Stock Part", sku="OOS-001",
            brand="Generic", price=200, stock_quantity=0,
            description="Out of stock", status="active"
        )
        db.session.add_all([p1, p2, p_oos])
        db.session.flush()

        # Create a cart with items for p1
        cart = Cart(user_id=user.id)
        db.session.add(cart)
        db.session.flush()

        cart_item = CartItem(cart_id=cart.id, product_id=p1.id, quantity=2)
        db.session.add(cart_item)

        # Create a default address
        addr = Address(
            user_id=user.id,
            full_name="Buy Now User",
            phone="9876543211",
            address_line_1="123 Test St",
            city="Chennai",
            state="Tamil Nadu",
            postal_code="600001",
            country="India",
            is_default=True
        )
        db.session.add(addr)
        db.session.commit()

        yield app

        db.session.remove()
        db.drop_all()


def login(client, email="buynow@example.com", password="pass123"):
    return client.post(
        '/auth/login',
        data={'email': email, 'password': password},
        follow_redirects=True
    )


def get_checkout_nonce(client, buy_now=False):
    """GET the checkout page to obtain a fresh nonce, return it."""
    url = '/orders/checkout?mode=buy_now' if buy_now else '/orders/checkout'
    client.get(url)
    with client.session_transaction() as sess:
        return sess.get('checkout_nonce', '')


# ─── TEST 1: Buy Now sets session and redirects to checkout ──────────────────

def test_buy_now_sets_session_and_redirects(app_context):
    client = app_context.test_client()
    login(client)

    with app_context.app_context():
        p2 = Product.query.filter_by(sku="SEAL-25").first()
        p2_id = p2.id

    with client.session_transaction() as sess:
        # Clear any stale buy_now
        sess.pop('buy_now', None)

    res = client.post('/cart/buy-now', data={
        'product_id': p2_id,
        'quantity': 2
    }, follow_redirects=False)

    # Should redirect to checkout?mode=buy_now
    assert res.status_code in (302, 303)
    assert 'checkout' in res.location
    assert 'buy_now' in res.location

    # Session must contain the buy_now data
    with client.session_transaction() as sess:
        assert 'buy_now' in sess
        assert sess['buy_now']['product_id'] == p2_id
        assert sess['buy_now']['quantity'] == 2


# ─── TEST 2: Buy Now checkout shows only selected product, NOT cart items ─────

def test_buy_now_checkout_shows_only_buy_now_product(app_context):
    client = app_context.test_client()
    login(client)

    with app_context.app_context():
        p2 = Product.query.filter_by(sku="SEAL-25").first()
        p2_id = p2.id

    # Set buy_now session manually
    with client.session_transaction() as sess:
        sess['buy_now'] = {'product_id': p2_id, 'quantity': 1}

    res = client.get('/orders/checkout?mode=buy_now')
    assert res.status_code == 200
    assert b'SEAL-25' in res.data or b'Mechanical Seal' in res.data
    # Cart bearing should NOT appear
    assert b'BRG-6203' not in res.data


# ─── TEST 3: Cart items remain unchanged after Buy Now purchase ───────────────

def test_cart_remains_unchanged_after_buy_now(app_context):
    client = app_context.test_client()
    login(client)

    with app_context.app_context():
        user = User.query.filter_by(email="buynow@example.com").first()
        p2 = Product.query.filter_by(sku="SEAL-25").first()
        addr = Address.query.filter_by(user_id=user.id).first()
        p2_id = p2.id
        addr_id = addr.id
        # Record cart state before
        cart = Cart.query.filter_by(user_id=user.id).first()
        original_cart_count = sum(i.quantity for i in cart.items)

    # Set buy_now session
    with client.session_transaction() as sess:
        sess['buy_now'] = {'product_id': p2_id, 'quantity': 1}

    # GET checkout to generate nonce, then POST
    nonce = get_checkout_nonce(client, buy_now=True)
    res = client.post('/orders/checkout?mode=buy_now', data={
        'address_id': addr_id,
        'payment_method': 'Cash on Delivery',
        'checkout_nonce': nonce,
    }, follow_redirects=True)

    assert res.status_code == 200

    with app_context.app_context():
        user = User.query.filter_by(email="buynow@example.com").first()
        cart = Cart.query.filter_by(user_id=user.id).first()
        # Cart items must remain as before the Buy Now
        after_count = sum(i.quantity for i in cart.items)
        assert after_count == original_cart_count

        # Buy Now product (Mechanical Seal / p2) must NOT be in cart
        p2 = Product.query.filter_by(sku="SEAL-25").first()
        cart_item_ids = [i.product_id for i in cart.items]
        assert p2.id not in cart_item_ids

        # An order must have been created for p2
        orders = Order.query.filter_by(user_id=user.id).all()
        assert any(
            any(oi.sku == "SEAL-25" for oi in o.items)
            for o in orders
        )


# ─── TEST 4: Stock validation rejects insufficient stock ─────────────────────

def test_buy_now_rejects_insufficient_stock(app_context):
    client = app_context.test_client()
    login(client)

    with app_context.app_context():
        p2 = Product.query.filter_by(sku="SEAL-25").first()
        p2_id = p2.id
        stock = p2.stock_quantity  # 5

    res = client.post('/cart/buy-now', data={
        'product_id': p2_id,
        'quantity': stock + 10  # way over stock
    }, follow_redirects=True)

    assert res.status_code == 200
    assert b'Only' in res.data or b'available' in res.data


# ─── TEST 5: Out of stock product is blocked ──────────────────────────────────

def test_buy_now_blocks_out_of_stock(app_context):
    client = app_context.test_client()
    login(client)

    with app_context.app_context():
        p_oos = Product.query.filter_by(sku="OOS-001").first()
        p_oos_id = p_oos.id

    res = client.post('/cart/buy-now', data={
        'product_id': p_oos_id,
        'quantity': 1
    }, follow_redirects=True)

    assert res.status_code == 200
    assert b'out of stock' in res.data.lower() or b'Out of Stock' in res.data


# ─── TEST 6: Unauthenticated redirect preserves buy_now session ──────────────

def test_buy_now_unauthenticated_redirects_to_login(app_context):
    client = app_context.test_client()

    with app_context.app_context():
        p2 = Product.query.filter_by(sku="SEAL-25").first()
        p2_id = p2.id

    res = client.post('/cart/buy-now', data={
        'product_id': p2_id,
        'quantity': 1
    }, follow_redirects=False)

    # Must redirect (to login)
    assert res.status_code in (302, 303)
    assert 'login' in res.location

    # Session must still hold buy_now
    with client.session_transaction() as sess:
        assert 'buy_now' in sess
        assert sess['buy_now']['product_id'] == p2_id


# ─── TEST 7: Server uses database price, not client-supplied ─────────────────

def test_buy_now_uses_database_price(app_context):
    client = app_context.test_client()
    login(client)

    with app_context.app_context():
        user = User.query.filter_by(email="buynow@example.com").first()
        p2 = Product.query.filter_by(sku="SEAL-25").first()
        addr = Address.query.filter_by(user_id=user.id).first()
        p2_id = p2.id
        db_price = float(p2.effective_price)
        addr_id = addr.id

    with client.session_transaction() as sess:
        sess['buy_now'] = {'product_id': p2_id, 'quantity': 1}

    # GET checkout to generate nonce, then POST
    nonce = get_checkout_nonce(client, buy_now=True)
    res = client.post('/orders/checkout?mode=buy_now', data={
        'address_id': addr_id,
        'payment_method': 'Cash on Delivery',
        'checkout_nonce': nonce,
    }, follow_redirects=True)

    assert res.status_code == 200

    with app_context.app_context():
        user = User.query.filter_by(email="buynow@example.com").first()
        orders = Order.query.filter_by(user_id=user.id).order_by(Order.id.desc()).all()
        buy_now_order = next(
            (o for o in orders if any(oi.sku == "SEAL-25" for oi in o.items)),
            None
        )
        assert buy_now_order is not None
        # Price must match DB price (700), not any client-injected value
        item = next(oi for oi in buy_now_order.items if oi.sku == "SEAL-25")
        assert float(item.unit_price) == db_price


# ─── TEST 8: Stock reduced correctly after Buy Now ───────────────────────────

def test_buy_now_reduces_stock(app_context):
    client = app_context.test_client()
    login(client)

    with app_context.app_context():
        user = User.query.filter_by(email="buynow@example.com").first()
        p2 = Product.query.filter_by(sku="SEAL-25").first()
        addr = Address.query.filter_by(user_id=user.id).first()
        p2_id = p2.id
        initial_stock = p2.stock_quantity
        addr_id = addr.id
        qty = 2

    with client.session_transaction() as sess:
        sess['buy_now'] = {'product_id': p2_id, 'quantity': qty}

    nonce = get_checkout_nonce(client, buy_now=True)
    client.post('/orders/checkout?mode=buy_now', data={
        'address_id': addr_id,
        'payment_method': 'Cash on Delivery',
        'checkout_nonce': nonce,
    }, follow_redirects=True)

    with app_context.app_context():
        p2 = Product.query.filter_by(sku="SEAL-25").first()
        assert p2.stock_quantity == initial_stock - qty


# ─── TEST 9: Buy Now order appears in order history ──────────────────────────

def test_buy_now_order_appears_in_history(app_context):
    client = app_context.test_client()
    login(client)

    with app_context.app_context():
        user = User.query.filter_by(email="buynow@example.com").first()
        p2 = Product.query.filter_by(sku="SEAL-25").first()
        addr = Address.query.filter_by(user_id=user.id).first()
        p2_id = p2.id
        addr_id = addr.id

    with client.session_transaction() as sess:
        sess['buy_now'] = {'product_id': p2_id, 'quantity': 1}

    nonce = get_checkout_nonce(client, buy_now=True)
    client.post('/orders/checkout?mode=buy_now', data={
        'address_id': addr_id,
        'payment_method': 'Cash on Delivery',
        'checkout_nonce': nonce,
    }, follow_redirects=True)

    res = client.get('/orders/')
    assert res.status_code == 200
    assert b'SP-' in res.data  # Order number prefix


# ─── TEST 10: Buy Now session cleared after successful order ─────────────────

def test_buy_now_session_cleared_after_order(app_context):
    client = app_context.test_client()
    login(client)

    with app_context.app_context():
        user = User.query.filter_by(email="buynow@example.com").first()
        p2 = Product.query.filter_by(sku="SEAL-25").first()
        addr = Address.query.filter_by(user_id=user.id).first()
        p2_id = p2.id
        addr_id = addr.id

    with client.session_transaction() as sess:
        sess['buy_now'] = {'product_id': p2_id, 'quantity': 1}

    nonce = get_checkout_nonce(client, buy_now=True)
    client.post('/orders/checkout?mode=buy_now', data={
        'address_id': addr_id,
        'payment_method': 'Cash on Delivery',
        'checkout_nonce': nonce,
    }, follow_redirects=True)

    with client.session_transaction() as sess:
        assert 'buy_now' not in sess

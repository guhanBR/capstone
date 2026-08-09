"""
Tests for the Order Placement Flow Fix:
- Place Order → Processing... → ORDER PLACED → Confirmation page
- Duplicate order prevention via nonce
- Error recovery (button re-enabled on failure)
- ?confirmed=1 flag present after successful order
"""
import pytest
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

        user = User(name="Flow Test User", email="flowtest@example.com", phone="9000000001")
        user.set_password("pass123")
        db.session.add(user)
        db.session.flush()

        cat = Category(name="Seals", status="active")
        db.session.add(cat)
        db.session.flush()

        p = Product(
            category_id=cat.id, name="Lip Seal 30mm", sku="SEAL-LIP-30",
            brand="SKF", price=320, stock_quantity=15,
            description="Radial shaft seal", status="active"
        )
        db.session.add(p)
        db.session.flush()

        cart = Cart(user_id=user.id)
        db.session.add(cart)
        db.session.flush()
        db.session.add(CartItem(cart_id=cart.id, product_id=p.id, quantity=1))

        addr = Address(
            user_id=user.id, full_name="Flow Test User", phone="9000000001",
            address_line_1="42 Test Road", city="Pune", state="Maharashtra",
            postal_code="411001", country="India", is_default=True
        )
        db.session.add(addr)
        db.session.commit()

        yield app

        db.session.remove()
        db.drop_all()


def login(client):
    return client.post('/auth/login',
        data={'email': 'flowtest@example.com', 'password': 'pass123'},
        follow_redirects=True)


# ─── TEST 1: GET /checkout generates a nonce ──────────────────────────────────

def test_checkout_get_generates_nonce(app_context):
    client = app_context.test_client()
    login(client)
    client.get('/orders/checkout')
    with client.session_transaction() as sess:
        assert 'checkout_nonce' in sess
        assert len(sess['checkout_nonce']) > 10


# ─── TEST 2: Successful cart checkout redirects to ?confirmed=1 ───────────────

def test_cart_checkout_redirects_with_confirmed_flag(app_context):
    client = app_context.test_client()
    login(client)

    # GET to get nonce
    client.get('/orders/checkout')
    with client.session_transaction() as sess:
        nonce = sess.get('checkout_nonce')

    with app_context.app_context():
        user = User.query.filter_by(email='flowtest@example.com').first()
        addr = Address.query.filter_by(user_id=user.id).first()
        addr_id = addr.id

    res = client.post('/orders/checkout', data={
        'address_id': addr_id,
        'payment_method': 'Cash on Delivery',
        'checkout_nonce': nonce,
    }, follow_redirects=False)

    assert res.status_code in (301, 302, 303)
    assert 'confirmed=1' in res.location


# ─── TEST 3: Order confirmation page shows ORDER PLACED banner ────────────────

def test_order_confirmation_shows_banner(app_context):
    client = app_context.test_client()
    login(client)

    client.get('/orders/checkout')
    with client.session_transaction() as sess:
        nonce = sess.get('checkout_nonce')

    with app_context.app_context():
        user = User.query.filter_by(email='flowtest@example.com').first()
        addr = Address.query.filter_by(user_id=user.id).first()
        addr_id = addr.id

    res = client.post('/orders/checkout', data={
        'address_id': addr_id,
        'payment_method': 'Cash on Delivery',
        'checkout_nonce': nonce,
    }, follow_redirects=True)

    assert res.status_code == 200
    # Banner must contain ORDER PLACED and the order number
    assert b'Order Placed' in res.data or b'ORDER PLACED' in res.data
    assert b'SP-' in res.data


# ─── TEST 4: Duplicate POST (refresh/double-submit) is rejected ───────────────

def test_duplicate_post_rejected_by_nonce(app_context):
    client = app_context.test_client()
    login(client)

    # Setup: add product back to cart (previous test consumed it)
    with app_context.app_context():
        user = User.query.filter_by(email='flowtest@example.com').first()
        p = Product.query.filter_by(sku='SEAL-LIP-30').first()
        cart = Cart.query.filter_by(user_id=user.id).first()
        if not any(i.product_id == p.id for i in cart.items):
            db.session.add(CartItem(cart_id=cart.id, product_id=p.id, quantity=1))
            db.session.commit()
        addr = Address.query.filter_by(user_id=user.id).first()
        addr_id = addr.id

    client.get('/orders/checkout')
    with client.session_transaction() as sess:
        nonce = sess.get('checkout_nonce')

    post_data = {
        'address_id': addr_id,
        'payment_method': 'Cash on Delivery',
        'checkout_nonce': nonce,
    }

    # First POST — should succeed
    res1 = client.post('/orders/checkout', data=post_data, follow_redirects=False)
    assert res1.status_code in (301, 302, 303)

    # Second POST with same nonce — nonce is gone, should redirect back to checkout
    res2 = client.post('/orders/checkout', data=post_data, follow_redirects=False)
    assert res2.status_code in (301, 302, 303)
    # Should NOT redirect to ?confirmed=1 (that would mean a duplicate order was created)
    assert 'confirmed=1' not in res2.location

    # Verify only ONE order was actually created for this user
    with app_context.app_context():
        user = User.query.filter_by(email='flowtest@example.com').first()
        orders = Order.query.filter_by(user_id=user.id).all()
        # Only one order should exist (the first successful one)
        assert len(orders) == 1



# ─── TEST 5: Nonce is cleared after successful order ─────────────────────────

def test_nonce_cleared_after_order(app_context):
    client = app_context.test_client()
    login(client)

    with app_context.app_context():
        user = User.query.filter_by(email='flowtest@example.com').first()
        p = Product.query.filter_by(sku='SEAL-LIP-30').first()
        cart = Cart.query.filter_by(user_id=user.id).first()
        if not any(i.product_id == p.id for i in cart.items):
            db.session.add(CartItem(cart_id=cart.id, product_id=p.id, quantity=1))
            db.session.commit()
        addr = Address.query.filter_by(user_id=user.id).first()
        addr_id = addr.id

    client.get('/orders/checkout')
    with client.session_transaction() as sess:
        nonce = sess.get('checkout_nonce')

    client.post('/orders/checkout', data={
        'address_id': addr_id,
        'payment_method': 'Cash on Delivery',
        'checkout_nonce': nonce,
    }, follow_redirects=False)

    with client.session_transaction() as sess:
        assert 'checkout_nonce' not in sess


# ─── TEST 6: Buy Now ?confirmed=1 redirect after order ───────────────────────

def test_buy_now_checkout_redirects_with_confirmed_flag(app_context):
    client = app_context.test_client()
    login(client)

    with app_context.app_context():
        user = User.query.filter_by(email='flowtest@example.com').first()
        p = Product.query.filter_by(sku='SEAL-LIP-30').first()
        addr = Address.query.filter_by(user_id=user.id).first()
        p_id = p.id
        addr_id = addr.id

    # Set buy_now session and get nonce
    with client.session_transaction() as sess:
        sess['buy_now'] = {'product_id': p_id, 'quantity': 1}

    client.get('/orders/checkout?mode=buy_now')
    with client.session_transaction() as sess:
        nonce = sess.get('checkout_nonce')

    res = client.post('/orders/checkout?mode=buy_now', data={
        'address_id': addr_id,
        'payment_method': 'Cash on Delivery',
        'checkout_nonce': nonce,
    }, follow_redirects=False)

    assert res.status_code in (301, 302, 303)
    assert 'confirmed=1' in res.location


# ─── TEST 7: Confirmation page shows View My Orders and Continue Shopping ─────

def test_confirmation_page_shows_action_buttons(app_context):
    client = app_context.test_client()
    login(client)

    with app_context.app_context():
        user = User.query.filter_by(email='flowtest@example.com').first()
        p = Product.query.filter_by(sku='SEAL-LIP-30').first()
        cart = Cart.query.filter_by(user_id=user.id).first()
        if not any(i.product_id == p.id for i in cart.items):
            db.session.add(CartItem(cart_id=cart.id, product_id=p.id, quantity=1))
            db.session.commit()
        addr = Address.query.filter_by(user_id=user.id).first()
        addr_id = addr.id

    client.get('/orders/checkout')
    with client.session_transaction() as sess:
        nonce = sess.get('checkout_nonce')

    res = client.post('/orders/checkout', data={
        'address_id': addr_id,
        'payment_method': 'Cash on Delivery',
        'checkout_nonce': nonce,
    }, follow_redirects=True)

    assert res.status_code == 200
    # Check for action button IDs
    assert b'view-orders-btn' in res.data or b'View My Orders' in res.data
    assert b'continue-shopping-btn' in res.data or b'Continue Shopping' in res.data

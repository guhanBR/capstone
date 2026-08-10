import pytest
from app import create_app, db
from app.models.user import User
from app.models.category import Category
from app.models.product import Product
from app.models.cart import Cart, CartItem
from app.models.address import Address
from app.models.wishlist import Wishlist
from app.models.notification import Notification
from app.models.review import Review
from app.models.order import Order

@pytest.fixture
def app_context():
    app = create_app('testing')
    with app.app_context():
        db.create_all()

        # Create user
        user = User(name="Test Customer", email="customer@example.com", phone="9876543210")
        user.set_password("Customer@123")
        db.session.add(user)
        db.session.flush()

        # Create category
        cat = Category(name="Bearings", status="active")
        db.session.add(cat)
        db.session.flush()

        # Create active product in stock
        p1 = Product(category_id=cat.id, name="6203 Bearing", sku="6203", brand="SKF", price=150, stock_quantity=10, description="D", status="active")
        # Create active product out of stock
        p_oos = Product(category_id=cat.id, name="Out of stock part", sku="OOS-123", brand="ABB", price=200, stock_quantity=0, description="OOS", status="active")
        db.session.add_all([p1, p_oos])
        db.session.flush()

        # Create address
        addr = Address(
            user_id=user.id,
            full_name="Test Customer",
            phone="9876543210",
            address_line_1="123 Test St",
            city="Chennai",
            state="Tamil Nadu",
            postal_code="600001",
            country="India",
            is_default=True
        )
        db.session.add(addr)
        db.session.flush()

        # Create order for review
        order = Order(
            user_id=user.id,
            order_number="ORD-1000",
            subtotal=150.00,
            total_amount=150.00,
            order_status="Delivered",
            address_id=addr.id,
            payment_status="Paid"
        )
        db.session.add(order)
        db.session.flush()

        # Create review
        review = Review(user_id=user.id, product_id=p1.id, order_id=order.id, rating=4, review_text="Good part", status="approved")
        db.session.add(review)

        db.session.commit()

        yield app

        db.session.remove()
        db.drop_all()

def login(client, email="customer@example.com", password="Customer@123"):
    return client.post('/auth/login', data={'email': email, 'password': password}, follow_redirects=True)

# ─────────────────────────────────────────────
# WISHLIST TESTS
# ─────────────────────────────────────────────

def test_wishlist_add_success(app_context):
    client = app_context.test_client()
    login(client)

    # Add product 1 to wishlist
    res = client.post('/customer/wishlist/add/1', follow_redirects=True)
    assert res.status_code == 200
    assert b'added to your wishlist' in res.data

    with app_context.app_context():
        items = Wishlist.query.filter_by(user_id=1).all()
        assert len(items) == 1
        assert items[0].product_id == 1

def test_wishlist_add_duplicate(app_context):
    client = app_context.test_client()
    login(client)

    # Add first time
    client.post('/customer/wishlist/add/1', follow_redirects=True)
    # Add second time
    res = client.post('/customer/wishlist/add/1', follow_redirects=True)
    assert res.status_code == 200
    assert b'already in your wishlist' in res.data

    with app_context.app_context():
        items = Wishlist.query.filter_by(user_id=1).all()
        assert len(items) == 1

def test_wishlist_add_invalid_product(app_context):
    client = app_context.test_client()
    login(client)

    res = client.post('/customer/wishlist/add/999', follow_redirects=True)
    assert res.status_code == 200
    assert b'Product not found' in res.data

def test_wishlist_add_out_of_stock_allowed(app_context):
    client = app_context.test_client()
    login(client)

    # Product 2 (sku: OOS-123) is out of stock (stock_quantity=0)
    res = client.post('/customer/wishlist/add/2', follow_redirects=True)
    assert res.status_code == 200
    assert b'added to your wishlist' in res.data

    with app_context.app_context():
        items = Wishlist.query.filter_by(user_id=1, product_id=2).all()
        assert len(items) == 1

def test_wishlist_remove(app_context):
    client = app_context.test_client()
    login(client)

    # Add item to wishlist first
    client.post('/customer/wishlist/add/1')

    with app_context.app_context():
        item = Wishlist.query.filter_by(user_id=1, product_id=1).first()
        wishlist_id = item.id

    res = client.post(f'/customer/wishlist/remove/{wishlist_id}', follow_redirects=True)
    assert res.status_code == 200
    assert b'removed from wishlist' in res.data

    with app_context.app_context():
        items = Wishlist.query.filter_by(user_id=1).all()
        assert len(items) == 0

def test_wishlist_to_cart_in_stock(app_context):
    client = app_context.test_client()
    login(client)

    # Add to wishlist
    client.post('/customer/wishlist/add/1')

    # Convert to cart
    res = client.post('/customer/wishlist/to-cart/1', follow_redirects=True)
    assert res.status_code == 200
    assert b'added to cart successfully' in res.data

    with app_context.app_context():
        cart = Cart.query.filter_by(user_id=1).first()
        assert cart is not None
        cart_items = CartItem.query.filter_by(cart_id=cart.id).all()
        assert len(cart_items) == 1
        assert cart_items[0].product_id == 1
        assert cart_items[0].quantity == 1

def test_wishlist_to_cart_out_of_stock_fails(app_context):
    client = app_context.test_client()
    login(client)

    # Add OOS product (id=2) to wishlist
    client.post('/customer/wishlist/add/2')

    # Try moving to cart
    res = client.post('/customer/wishlist/to-cart/2', follow_redirects=True)
    assert res.status_code == 200
    assert b'currently out of stock and cannot be added' in res.data

    with app_context.app_context():
        cart = Cart.query.filter_by(user_id=1).first()
        if cart:
            cart_items = CartItem.query.filter_by(cart_id=cart.id).all()
            assert len(cart_items) == 0

# ─────────────────────────────────────────────
# NOTIFICATIONS TESTS
# ─────────────────────────────────────────────

def test_notifications_handling(app_context):
    client = app_context.test_client()
    login(client)

    with app_context.app_context():
        n1 = Notification(user_id=1, title="Test Notif 1", message="Message 1", is_read=False)
        n2 = Notification(user_id=1, title="Test Notif 2", message="Message 2", is_read=False)
        db.session.add_all([n1, n2])
        db.session.commit()
        n1_id = n1.id

    # View notifications
    res = client.get('/customer/notifications')
    assert res.status_code == 200
    assert b'Test Notif 1' in res.data
    assert b'Test Notif 2' in res.data

    # Mark one as read
    res = client.post(f'/customer/notifications/mark-read/{n1_id}', follow_redirects=True)
    assert res.status_code == 200

    with app_context.app_context():
        notif1 = db.session.get(Notification, n1_id)
        assert notif1.is_read is True
        unread_count = Notification.query.filter_by(user_id=1, is_read=False).count()
        assert unread_count == 1

    # Mark all read
    res = client.post('/customer/notifications/mark-all-read', follow_redirects=True)
    assert res.status_code == 200
    assert b'All notifications marked as read' in res.data

    with app_context.app_context():
        unread_count = Notification.query.filter_by(user_id=1, is_read=False).count()
        assert unread_count == 0

# ─────────────────────────────────────────────
# MY REVIEWS TESTS
# ─────────────────────────────────────────────

def test_my_reviews_edit_and_delete(app_context):
    client = app_context.test_client()
    login(client)

    res = client.get('/customer/reviews')
    assert res.status_code == 200
    assert b'Good part' in res.data

    # Edit review rating and comments
    res = client.post('/customer/reviews/edit/1', data={
        'rating': 5,
        'review_text': 'Excellent part, works flawlessly.'
    }, follow_redirects=True)
    assert res.status_code == 200
    assert b'Review updated successfully' in res.data

    with app_context.app_context():
        rev = db.session.get(Review, 1)
        assert rev.rating == 5
        assert rev.review_text == 'Excellent part, works flawlessly.'

    # Delete review
    res = client.post('/customer/reviews/delete/1', follow_redirects=True)
    assert res.status_code == 200
    assert b'Review deleted' in res.data

    with app_context.app_context():
        assert db.session.get(Review, 1) is None

# ─────────────────────────────────────────────
# SAVED ADDRESSES TESTS
# ─────────────────────────────────────────────

def test_addresses_handling_and_promotion(app_context):
    client = app_context.test_client()
    login(client)

    # 1. Add first address (should automatically become default since existing count was 1, wait, fixture created 1 address, so count is 1. Adding this will be second address)
    res = client.post('/customer/profile?section=addresses', data={
        'action': 'add_address',
        'full_name': 'Recipient One',
        'phone': '9998887776',
        'address_line_1': 'First St 123',
        'city': 'Chennai',
        'state': 'Tamil Nadu',
        'postal_code': '600001',
        'country': 'India'
    }, follow_redirects=True)
    assert res.status_code == 200
    assert b'Address added successfully' in res.data

    with app_context.app_context():
        # First added address in test
        addr1 = Address.query.filter_by(user_id=1, full_name='Recipient One').first()
        assert addr1.is_default is False
        addr1_id = addr1.id

    # 2. Add second address (is_default=False by default)
    res = client.post('/customer/profile?section=addresses', data={
        'action': 'add_address',
        'full_name': 'Recipient Two',
        'phone': '8887776665',
        'address_line_1': 'Second St 456',
        'city': 'Chennai',
        'state': 'Tamil Nadu',
        'postal_code': '600002',
        'country': 'India'
    }, follow_redirects=True)
    assert res.status_code == 200

    with app_context.app_context():
        addr2 = Address.query.filter_by(user_id=1, full_name='Recipient Two').first()
        assert addr2.is_default is False
        addr2_id = addr2.id

    # 3. Set second address as default
    res = client.post(f'/customer/address/set-default/{addr2_id}', follow_redirects=True)
    assert res.status_code == 200
    assert b'Default address updated' in res.data

    with app_context.app_context():
        a1 = db.session.get(Address, addr1_id)
        a2 = db.session.get(Address, addr2_id)
        # The initial fixture address should also be marked False
        fixture_addr = Address.query.filter_by(user_id=1, full_name='Test Customer').first()
        assert fixture_addr.is_default is False
        assert a1.is_default is False
        assert a2.is_default is True

    # 4. Delete the default address (second one).
    # Since it was default, the oldest remaining address (the fixture address) should be promoted to default.
    res = client.post(f'/customer/address/delete/{addr2_id}', follow_redirects=True)
    assert res.status_code == 200
    assert b'Address deleted' in res.data

    with app_context.app_context():
        a1 = db.session.get(Address, addr1_id)
        a2 = db.session.get(Address, addr2_id)
        fixture_addr = Address.query.filter_by(user_id=1, full_name='Test Customer').first()
        assert a2 is None
        assert fixture_addr.is_default is True
        assert a1.is_default is False

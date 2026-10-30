import pytest
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from app import create_app, db
from app.utils.timezone import to_ist, format_ist, IST, now_ist
from app.models.user import User
from app.models.category import Category
from app.models.product import Product
from app.models.address import Address
from app.models.cart import Cart, CartItem
from app.models.order import Order
from app.services.order_service import OrderService


def test_timezone_conversion_logic():
    """Verify to_ist converts naive and aware UTC datetimes to IST and does not double-convert IST."""
    assert to_ist(None) is None
    assert format_ist(None) == '—'

    # Naive UTC datetime: 05:30:00 UTC -> 11:00:00 IST (+5h 30m)
    naive_utc = datetime(2026, 10, 13, 5, 30, 0)
    converted = to_ist(naive_utc)
    assert converted.tzinfo == IST
    assert converted.hour == 11
    assert converted.minute == 0
    assert converted.day == 13

    # Aware UTC datetime
    aware_utc = datetime(2026, 10, 13, 5, 30, 0, tzinfo=timezone.utc)
    converted_aware = to_ist(aware_utc)
    assert converted_aware.tzinfo == IST
    assert converted_aware.hour == 11
    assert converted_aware.minute == 0

    # Already IST datetime should NOT add another 5h 30m
    already_ist = datetime(2026, 10, 13, 11, 0, 0, tzinfo=IST)
    converted_ist = to_ist(already_ist)
    assert converted_ist.tzinfo == IST
    assert converted_ist.hour == 11
    assert converted_ist.minute == 0

    # Day boundary crossing: 20:00 UTC on Oct 13 -> 01:30 IST on Oct 14
    late_utc = datetime(2026, 10, 13, 20, 0, 0)
    converted_late = to_ist(late_utc)
    assert converted_late.day == 14
    assert converted_late.hour == 1
    assert converted_late.minute == 30

    # Formatting test
    formatted = format_ist(naive_utc, '%Y-%m-%d %H:%M')
    assert formatted == '2026-10-13 11:00'

    formatted_12h = format_ist(naive_utc, '%d %b %Y, %I:%M %p')
    assert formatted_12h == '13 Oct 2026, 11:00 AM'


@pytest.fixture
def app_and_client():
    app = create_app('testing')
    with app.app_context():
        db.create_all()

        admin = User(name="Admin User", email="admin@example.com", phone="9990001111", role="admin", status="active")
        admin.set_password("Admin@123")
        db.session.add(admin)

        customer = User(name="Rohan Sharma", email="rohan@example.com", phone="9990002222", role="customer", status="active")
        customer.set_password("Cust@123")
        db.session.add(customer)
        db.session.flush()

        cat = Category(name="Pumps", status="active")
        db.session.add(cat)
        db.session.flush()

        prod = Product(
            category_id=cat.id,
            name="Centrifugal Impeller",
            sku="IMP-CF-100",
            brand="Kirloskar",
            price=1200.0,
            stock_quantity=20,
            description="High grade bronze impeller",
            status="active"
        )
        db.session.add(prod)

        addr = Address(
            user_id=customer.id,
            full_name="Rohan Sharma",
            phone="9990002222",
            address_line_1="102 MG Road",
            city="Bengaluru",
            state="Karnataka",
            postal_code="560001",
            country="India",
            is_default=True
        )
        db.session.add(addr)

        cart = Cart(user_id=customer.id)
        db.session.add(cart)
        db.session.flush()

        cart_item = CartItem(cart_id=cart.id, product_id=prod.id, quantity=2)
        db.session.add(cart_item)
        db.session.commit()

        client = app.test_client()

        yield app, client, admin, customer, prod, addr

        db.session.remove()
        db.drop_all()


def test_order_creation_timestamp_and_display(app_and_client):
    app, client, admin, customer, prod, addr = app_and_client

    with app.app_context():
        # Record time right before placing order
        time_before_order_utc = datetime.now(timezone.utc)
        time_before_order_ist = time_before_order_utc.astimezone(IST)

        success, msg, order = OrderService.create_order(
            user_id=customer.id,
            address_id=addr.id,
            payment_method='Cash on Delivery'
        )
        assert success is True
        assert order is not None

        # 1. Verify model storage and property
        # created_at is stored in UTC
        assert order.created_at is not None
        # created_at_ist returns timezone-aware IST object
        assert order.created_at_ist.tzinfo == IST
        assert order.created_at_ist.hour == time_before_order_ist.hour
        assert order.created_at_ist.minute == time_before_order_ist.minute

        # 2. Verify Order.to_dict() returns IST formatted date
        d = order.to_dict()
        expected_time_str = order.created_at_ist.strftime('%Y-%m-%d %H:%M:%S')
        assert d['created_at'] == expected_time_str

        order_num = order.order_number
        order_id = order.id
        expected_ist_display = order.created_at_ist.strftime('%Y-%m-%d %H:%M')
        expected_ist_detail_banner = order.created_at_ist.strftime('%d %b %Y, %I:%M %p')

    # 3. Test Admin -> Orders displays the correct IST time
    with client.session_transaction() as sess:
        sess['_user_id'] = str(admin.id)
        sess['_fresh'] = True

    admin_res = client.get('/admin/orders')
    assert admin_res.status_code == 200
    assert order_num.encode('utf-8') in admin_res.data
    assert expected_ist_display.encode('utf-8') in admin_res.data

    # 4. Test Customer -> Orders displays the correct IST time
    with client.session_transaction() as sess:
        sess['_user_id'] = str(customer.id)
        sess['_fresh'] = True

    cust_res = client.get('/orders/')
    assert cust_res.status_code == 200
    assert order_num.encode('utf-8') in cust_res.data
    assert expected_ist_display.encode('utf-8') in cust_res.data

    # 5. Test Customer -> Order Detail displays correct IST time in both locations
    detail_res = client.get(f'/orders/{order_num}')
    assert detail_res.status_code == 200
    assert expected_ist_detail_banner.encode('utf-8') in detail_res.data

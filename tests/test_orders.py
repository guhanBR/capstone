import pytest
from app import create_app, db
from app.models.user import User
from app.models.category import Category
from app.models.product import Product
from app.models.address import Address
from app.models.cart import Cart, CartItem
from app.services.order_service import OrderService

@pytest.fixture
def app_context():
    app = create_app('testing')
    with app.app_context():
        db.create_all()
        user = User(name="Order User", email="order@example.com", phone="9876543210")
        user.set_password("pass123")
        db.session.add(user)
        db.session.flush()

        addr = Address(user_id=user.id, full_name="User", phone="9876543210", address_line_1="L1", city="C", state="S", postal_code="123")
        db.session.add(addr)

        cat = Category(name="Seals")
        db.session.add(cat)
        db.session.flush()

        p = Product(category_id=cat.id, name="25mm Seal", sku="S25", brand="Burgmann", price=500, stock_quantity=10, description="D")
        db.session.add(p)
        db.session.flush()

        cart = Cart(user_id=user.id)
        db.session.add(cart)
        db.session.flush()

        item = CartItem(cart_id=cart.id, product_id=p.id, quantity=3)
        db.session.add(item)
        db.session.commit()

        yield app

def test_order_creation_and_stock_reduction(app_context):
    with app_context.app_context():
        success, msg, order = OrderService.create_order(user_id=1, address_id=1)
        assert success is True
        assert order.subtotal == 1500.0
        assert order.total_amount == 1600.0  # 3 * 500 = 1500 subtotal + 100 shipping = 1600 total
        assert order.order_status == 'Pending'

        p = db.session.get(Product, 1)
        assert p.stock_quantity == 7  # 10 - 3 = 7

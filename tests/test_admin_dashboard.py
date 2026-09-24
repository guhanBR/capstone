import pytest
from app import create_app, db
from app.models.user import User
from app.models.product import Product
from app.models.category import Category
from app.models.order import Order

@pytest.fixture
def admin_client():
    app = create_app('testing')
    with app.app_context():
        db.create_all()
        admin = User(name="Admin User", email="admin@sparepro.com", phone="9876543210", role="admin", status="active")
        admin.set_password("password123")
        
        customer = User(name="John Doe", email="customer@example.com", phone="9876543211", role="customer", status="active")
        customer.set_password("password123")

        cat = Category(name="Bearings", status="active")
        db.session.add_all([admin, customer, cat])
        db.session.flush()

        p1 = Product(category_id=cat.id, name="Test Product", sku="TEST-001", brand="TestBrand", description="Test Description", price=100, stock_quantity=2, minimum_stock_level=5)
        db.session.add(p1)
        db.session.flush()

        o1 = Order(user_id=customer.id, order_number="ORD-1001", subtotal=100.0, total_amount=100.0, order_status="Pending")
        db.session.add(o1)
        db.session.commit()

        client = app.test_client()
        with client.session_transaction() as sess:
            sess['_user_id'] = str(admin.id)
            sess['_fresh'] = True

        yield client
        db.session.remove()
        db.drop_all()

def test_admin_dashboard_rendering(admin_client):
    res = admin_client.get('/admin/dashboard')
    assert res.status_code == 200
    assert b'Admin Dashboard' in res.data
    assert b'ADMIN' in res.data
    assert b'Total Revenue' in res.data
    assert b'Total Orders' in res.data
    assert b'Pending Orders' in res.data
    assert b'Total Products' in res.data
    assert b'Total Customers' in res.data
    assert b'Low / Out Stock' in res.data
    assert b'ORD-1001' in res.data
    assert b'TEST-001' in res.data
    assert b'/admin/orders' in res.data
    assert b'/admin/inventory' in res.data
    assert b'/admin/products/new' in res.data

def test_manager_dashboard_rendering():
    app = create_app('testing')
    with app.app_context():
        db.create_all()
        manager = User(name="Manager User", email="mgr@sparepro.com", phone="9876543210", role="manager", status="active")
        manager.set_password("password123")
        db.session.add(manager)
        db.session.commit()

        client = app.test_client()
        with client.session_transaction() as sess:
            sess['_user_id'] = str(manager.id)
            sess['_fresh'] = True

        res = client.get('/admin/dashboard')
        assert res.status_code == 200
        assert b'Manager Dashboard' in res.data
        assert b'MANAGER' in res.data
        assert b'Total Revenue' in res.data
        db.session.remove()
        db.drop_all()

def test_employee_dashboard_rendering():
    app = create_app('testing')
    with app.app_context():
        db.create_all()
        employee = User(name="Employee User", email="emp@sparepro.com", phone="9876543210", role="employee", status="active")
        employee.set_password("password123")
        db.session.add(employee)
        db.session.commit()

        client = app.test_client()
        with client.session_transaction() as sess:
            sess['_user_id'] = str(employee.id)
            sess['_fresh'] = True

        res = client.get('/admin/dashboard')
        assert res.status_code == 200
        assert b'Employee Dashboard' in res.data
        assert b'EMPLOYEE' in res.data
        assert b'Total Revenue' in res.data
        db.session.remove()
        db.drop_all()

import pytest
from app import create_app, db
from app.models.user import User
from app.models.category import Category
from app.models.product import Product
from app.models.order import Order
from app.models.review import Review

@pytest.fixture
def app():
    app = create_app('testing')
    with app.app_context():
        db.create_all()

        # Seed Owner/Admin
        admin = User(
            name="Owner Admin",
            email="owner@sparepro.local",
            phone="9998887770",
            role="admin",
            status="active"
        )
        admin.set_password("Admin@12345")

        # Seed Manager
        manager = User(
            name="Ops Manager",
            email="manager@sparepro.local",
            phone="9998887771",
            role="manager",
            status="active"
        )
        manager.set_password("Manager@12345")

        # Seed Employee
        employee = User(
            name="Store Employee",
            email="employee@sparepro.local",
            phone="9998887772",
            role="employee",
            status="active"
        )
        employee.set_password("Employee@12345")

        # Seed Customer
        customer = User(
            name="Test Customer",
            email="customer@example.com",
            phone="9998887773",
            role="customer",
            status="active"
        )
        customer.set_password("Customer@12345")

        # Seed Category & Product & Review
        cat = Category(name="Bearings", description="Motor Bearings", status="active")
        db.session.add_all([admin, manager, employee, customer, cat])
        db.session.commit()

        prod = Product(
            category_id=cat.id,
            name="Test Ball Bearing",
            sku="TEST-BRG-01",
            brand="SKF",
            description="Test description",
            price=500.00,
            stock_quantity=50,
            status="active"
        )
        db.session.add(prod)
        db.session.commit()

        order = Order(
            user_id=customer.id,
            order_number="ORD-TEST-001",
            subtotal=500.00,
            total_amount=500.00,
            order_status="Delivered",
            payment_status="Paid"
        )
        db.session.add(order)
        db.session.commit()

        rev = Review(
            user_id=customer.id,
            product_id=prod.id,
            order_id=order.id,
            rating=5,
            review_text="Great part!",
            status="approved"
        )
        db.session.add(rev)
        db.session.commit()

        yield app

        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()

def login_as(client, email, password):
    return client.post('/auth/login', data={'email': email, 'password': password}, follow_redirects=True)

# ----------------------------------------------------
# 1. OWNER / ADMIN ROLE TESTS
# ----------------------------------------------------
def test_owner_admin_full_access(client):
    login_as(client, 'owner@sparepro.local', 'Admin@12345')

    # All admin views must return 200
    endpoints = [
        '/admin/dashboard',
        '/admin/products',
        '/admin/products/new',
        '/admin/categories',
        '/admin/brands',
        '/admin/inventory',
        '/admin/orders',
        '/admin/customers',
        '/admin/reviews',
        '/admin/settings',
        '/admin/staff',
        '/admin/staff/new',
        '/reports/'
    ]
    for ep in endpoints:
        res = client.get(ep)
        assert res.status_code == 200, f"Owner should have access to {ep}, got {res.status_code}"

def test_owner_admin_staff_management_crud(client):
    login_as(client, 'owner@sparepro.local', 'Admin@12345')

    # 1. Create new staff member (Employee)
    res = client.post('/admin/staff/new', data={
        'name': 'New Staff Emp',
        'email': 'new.emp@sparepro.local',
        'phone': '9876543210',
        'role': 'employee',
        'status': 'active',
        'password': 'Password@123'
    }, follow_redirects=True)
    assert res.status_code == 200
    assert b"New Staff Emp" in res.data

    with client.application.app_context():
        created_user = User.query.filter_by(email='new.emp@sparepro.local').first()
        assert created_user is not None
        assert created_user.role == 'employee'
        assert created_user.check_password('Password@123')
        new_id = created_user.id

    # 2. Edit staff member & change role to manager
    res = client.post(f'/admin/staff/edit/{new_id}', data={
        'name': 'Promoted Manager',
        'phone': '9876543210',
        'role': 'manager',
        'status': 'active',
        'password': ''
    }, follow_redirects=True)
    assert res.status_code == 200
    assert b"Promoted Manager" in res.data

    with client.application.app_context():
        updated_user = db.session.get(User, new_id)
        assert updated_user.name == 'Promoted Manager'
        assert updated_user.role == 'manager'

    # 3. Toggle status
    res = client.post(f'/admin/staff/toggle-status/{new_id}', follow_redirects=True)
    assert res.status_code == 200
    with client.application.app_context():
        toggled_user = db.session.get(User, new_id)
        assert toggled_user.status == 'inactive'

def test_owner_protection_prevent_last_admin_lockout(client):
    login_as(client, 'owner@sparepro.local', 'Admin@12345')

    with client.application.app_context():
        owner = User.query.filter_by(email='owner@sparepro.local').first()
        owner_id = owner.id

    # Try deactivating the only active admin
    res = client.post(f'/admin/staff/toggle-status/{owner_id}', follow_redirects=True)
    assert b"Cannot deactivate the final active Owner/Admin account" in res.data

    with client.application.app_context():
        owner = db.session.get(User, owner_id)
        assert owner.status == 'active'

    # Try demoting the only active admin
    res = client.post(f'/admin/staff/edit/{owner_id}', data={
        'name': 'Owner Admin',
        'phone': '9998887770',
        'role': 'employee',
        'status': 'active'
    }, follow_redirects=True)
    assert b"Cannot demote the final active Owner/Admin account" in res.data

    with client.application.app_context():
        owner = db.session.get(User, owner_id)
        assert owner.role == 'admin'

# ----------------------------------------------------
# 2. MANAGER ROLE TESTS
# ----------------------------------------------------
def test_manager_access_permissions(client):
    login_as(client, 'manager@sparepro.local', 'Manager@12345')

    # Allowed routes
    allowed = [
        '/admin/dashboard',
        '/admin/products',
        '/admin/products/new',
        '/admin/categories',
        '/admin/brands',
        '/admin/inventory',
        '/admin/orders',
        '/admin/customers',
        '/admin/reviews',
        '/reports/',
        '/reports/export/sales'
    ]
    for ep in allowed:
        res = client.get(ep)
        assert res.status_code == 200, f"Manager should access {ep}, got {res.status_code}"

    # Forbidden Owner-only routes (must return 403)
    forbidden = [
        '/admin/staff',
        '/admin/staff/new',
        '/admin/settings'
    ]
    for ep in forbidden:
        res = client.get(ep)
        assert res.status_code == 403, f"Manager must be blocked from {ep} with 403, got {res.status_code}"

def test_manager_cannot_create_staff(client):
    login_as(client, 'manager@sparepro.local', 'Manager@12345')
    res = client.post('/admin/staff/new', data={
        'name': 'Hacker Staff',
        'email': 'hacker@sparepro.local',
        'phone': '9999999999',
        'role': 'admin',
        'password': 'Password@123'
    })
    assert res.status_code == 403

# ----------------------------------------------------
# 3. EMPLOYEE ROLE TESTS
# ----------------------------------------------------
def test_employee_operational_access(client):
    login_as(client, 'employee@sparepro.local', 'Employee@12345')

    # Allowed operational view routes
    allowed = [
        '/admin/dashboard',
        '/admin/products',
        '/admin/categories',
        '/admin/brands',
        '/admin/inventory',
        '/admin/orders',
        '/admin/customers',
        '/admin/reviews'
    ]
    for ep in allowed:
        res = client.get(ep)
        assert res.status_code == 200, f"Employee should access {ep}, got {res.status_code}"

def test_employee_restricted_routes_forbidden(client):
    login_as(client, 'employee@sparepro.local', 'Employee@12345')

    # GET routes that must return 403 for Employee
    forbidden_get = [
        '/admin/products/new',
        '/admin/products/edit/1',
        '/admin/staff',
        '/admin/staff/new',
        '/admin/settings',
        '/reports/',
        '/reports/export/sales',
        '/reports/export/products'
    ]
    for ep in forbidden_get:
        res = client.get(ep)
        assert res.status_code == 403, f"Employee must be blocked from GET {ep} with 403, got {res.status_code}"

    # POST routes that must return 403 for Employee
    forbidden_post = [
        ('/admin/products/new', {'name': 'New P', 'sku': 'SKU-099', 'price': '10', 'category_id': 1, 'brand': 'B', 'description': 'D'}),
        ('/admin/products/toggle-status/1', {}),
        ('/admin/categories', {'action': 'add', 'name': 'New Cat'}),
        ('/admin/brands/edit', {'old_brand_name': 'SKF', 'new_brand_name': 'SKF Renamed'}),
        ('/admin/customers/toggle-status/4', {}),
        ('/admin/reviews/delete/1', {}),
        ('/admin/staff/new', {}),
        ('/admin/staff/toggle-status/1', {})
    ]
    for ep, payload in forbidden_post:
        res = client.post(ep, data=payload)
        assert res.status_code == 403, f"Employee must be blocked from POST {ep} with 403, got {res.status_code}"

# ----------------------------------------------------
# 4. CUSTOMER REGRESSION & ACCESS CONTROL
# ----------------------------------------------------
def test_customer_cannot_access_admin(client):
    login_as(client, 'customer@example.com', 'Customer@12345')

    admin_endpoints = [
        '/admin/dashboard',
        '/admin/products',
        '/admin/orders',
        '/admin/staff',
        '/reports/'
    ]
    for ep in admin_endpoints:
        res = client.get(ep)
        assert res.status_code == 403, f"Customer must get 403 on {ep}, got {res.status_code}"

def test_customer_features_regression(client):
    login_as(client, 'customer@example.com', 'Customer@12345')

    # Customer routes must all work
    res = client.get('/')
    assert res.status_code == 200

    res = client.get('/products/')
    assert res.status_code == 200

    res = client.get('/customer/dashboard')
    assert res.status_code == 200

    res = client.get('/cart/')
    assert res.status_code == 200

    res = client.get('/orders/')
    assert res.status_code == 200

    res = client.get('/customer/profile')
    assert res.status_code == 200

    res = client.get('/customer/wishlist')
    assert res.status_code == 200

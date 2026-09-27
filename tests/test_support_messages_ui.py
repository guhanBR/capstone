import pytest
from app import create_app, db
from app.models.user import User

@pytest.fixture
def app_context():
    app = create_app('testing')
    with app.app_context():
        db.create_all()

        # Admin user
        admin = User(name="Test Admin", email="admin@sparepro.local", phone="9998887770", role="admin", status="active")
        admin.set_password("Admin@12345")

        # Manager user
        manager = User(name="Test Manager", email="manager@sparepro.local", phone="9998887771", role="manager", status="active")
        manager.set_password("Manager@12345")

        # Employee user
        employee = User(name="Test Employee", email="employee@sparepro.local", phone="9998887772", role="employee", status="active")
        employee.set_password("Employee@12345")

        # Customer user
        customer = User(name="Test Customer", email="customer@sparepro.local", phone="9998887773", role="customer", status="active")
        customer.set_password("Customer@123")

        db.session.add_all([admin, manager, employee, customer])
        db.session.commit()

        yield app

        db.session.remove()
        db.drop_all()


def login(client, email, password):
    return client.post('/auth/login', data={'email': email, 'password': password}, follow_redirects=True)


def test_admin_can_access_support_messages_page(app_context):
    client = app_context.test_client()
    login(client, "admin@sparepro.local", "Admin@12345")

    res = client.get('/admin/support-messages')
    assert res.status_code == 200
    assert b'Support Centre' in res.data
    assert b'View and manage customer support enquiries' in res.data


def test_manager_can_access_support_messages_page(app_context):
    client = app_context.test_client()
    login(client, "manager@sparepro.local", "Manager@12345")

    res = client.get('/admin/support-messages')
    assert res.status_code == 200
    assert b'Support Centre' in res.data


def test_employee_cannot_access_support_messages_page(app_context):
    client = app_context.test_client()
    login(client, "employee@sparepro.local", "Employee@12345")

    res = client.get('/admin/support-messages')
    assert res.status_code == 403


def test_customer_cannot_access_support_messages_page(app_context):
    client = app_context.test_client()
    login(client, "customer@sparepro.local", "Customer@123")

    res = client.get('/admin/support-messages')
    assert res.status_code == 403


def test_unauthenticated_cannot_access_support_messages_page(app_context):
    client = app_context.test_client()

    res = client.get('/admin/support-messages')
    assert res.status_code == 302
    assert '/auth/login' in res.location

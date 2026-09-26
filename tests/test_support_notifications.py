import pytest
from app import create_app, db
from app.models.user import User
from app.models.contact_message import ContactMessage

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

        # Unread message 1
        msg1 = ContactMessage(
            name="Rajesh Kumar",
            email="rajesh@example.com",
            phone="9876543210",
            subject="Impeller Bore Size",
            message="Please confirm bore dimension.",
            status="unread",
            is_read=False
        )

        # Unread message 2
        msg2 = ContactMessage(
            name="Suresh Patel",
            email="suresh@example.com",
            phone="9876543211",
            subject="Seal Material Query",
            message="Is Viton seal compatible?",
            status="unread",
            is_read=False
        )

        db.session.add_all([admin, manager, employee, msg1, msg2])
        db.session.commit()

        yield app

        db.session.remove()
        db.drop_all()


def login(client, email, password):
    return client.post('/auth/login', data={'email': email, 'password': password}, follow_redirects=True)


def test_unread_count_api_admin_and_manager(app_context):
    client = app_context.test_client()

    # Admin
    login(client, "admin@sparepro.local", "Admin@12345")
    res = client.get('/api/support-messages/unread-count')
    assert res.status_code == 200
    assert res.get_json()['unread_count'] == 2

    # Logout & Manager
    client.get('/auth/logout')
    login(client, "manager@sparepro.local", "Manager@12345")
    res_mgr = client.get('/api/support-messages/unread-count')
    assert res_mgr.status_code == 200
    assert res_mgr.get_json()['unread_count'] == 2


def test_unread_count_api_employee_and_unauthenticated_denied(app_context):
    client = app_context.test_client()

    # Unauthenticated
    res_unauth = client.get('/api/support-messages/unread-count')
    assert res_unauth.status_code == 401

    # Employee
    login(client, "employee@sparepro.local", "Employee@12345")
    res_emp = client.get('/api/support-messages/unread-count')
    assert res_emp.status_code == 403


def test_opening_message_details_marks_it_as_read(app_context):
    client = app_context.test_client()
    login(client, "admin@sparepro.local", "Admin@12345")

    # Initial count is 2
    res1 = client.get('/api/support-messages/unread-count')
    assert res1.get_json()['unread_count'] == 2

    # Open message 1 details
    res_detail = client.get('/api/support-messages/1')
    assert res_detail.status_code == 200
    assert res_detail.get_json()['data']['is_read'] is True

    # Check persistence in DB
    with app_context.app_context():
        msg = db.session.get(ContactMessage, 1)
        assert msg.is_read is True
        assert msg.read_at is not None
        assert msg.status == 'read'

    # Unread count should now decrease to 1
    res2 = client.get('/api/support-messages/unread-count')
    assert res2.get_json()['unread_count'] == 1


def test_explicit_mark_read_endpoint(app_context):
    client = app_context.test_client()
    login(client, "admin@sparepro.local", "Admin@12345")

    res = client.post('/api/support-messages/2/read')
    assert res.status_code == 200
    assert res.get_json()['success'] is True
    assert res.get_json()['data']['is_read'] is True

    with app_context.app_context():
        msg = db.session.get(ContactMessage, 2)
        assert msg.is_read is True
        assert msg.read_at is not None

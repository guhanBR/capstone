import pytest
from app import create_app, db
from app.models.user import User
from app.models.contact_message import ContactMessage

@pytest.fixture
def app_context():
    app = create_app('testing')
    with app.app_context():
        db.create_all()

        # Create Admin user
        admin = User(name="Test Admin", email="admin@sparepro.local", phone="9998887770", role="admin", status="active")
        admin.set_password("Admin@12345")

        # Create Manager user
        manager = User(name="Test Manager", email="manager@sparepro.local", phone="9998887771", role="manager", status="active")
        manager.set_password("Manager@12345")

        # Create Employee user
        employee = User(name="Test Employee", email="employee@sparepro.local", phone="9998887772", role="employee", status="active")
        employee.set_password("Employee@12345")

        # Create Customer user
        customer = User(name="Test Customer", email="customer@sparepro.local", phone="9998887773", role="customer", status="active")
        customer.set_password("Customer@123")

        db.session.add_all([admin, manager, employee, customer])
        db.session.flush()

        # Create sample contact messages
        msg1 = ContactMessage(
            name="Rajesh Kumar",
            email="rajesh@example.com",
            phone="9876543210",
            subject="Motor Bearing Query",
            message="What is the inner diameter of 6203-2RS bearing?",
            status="unread"
        )

        msg2 = ContactMessage(
            name="Suresh Patel",
            email="suresh@example.com",
            phone="9876543211",
            subject="Pump Shaft Material",
            message="Do you supply SS-316 pump shafts for chemical pumps?",
            status="read"
        )

        db.session.add_all([msg1, msg2])
        db.session.commit()

        yield app

        db.session.remove()
        db.drop_all()


def login(client, email, password):
    return client.post('/auth/login', data={'email': email, 'password': password}, follow_redirects=True)


# ─────────────────────────────────────────────
# 1. ADMIN PERMISSIONS & OPERATIONS
# ─────────────────────────────────────────────

def test_admin_can_retrieve_message_list(app_context):
    client = app_context.test_client()
    login(client, "admin@sparepro.local", "Admin@12345")

    res = client.get('/api/support-messages')
    assert res.status_code == 200
    json_data = res.get_json()
    assert json_data['success'] is True
    assert len(json_data['data']) == 2
    assert json_data['total'] == 2


def test_admin_can_retrieve_single_message_detail(app_context):
    client = app_context.test_client()
    login(client, "admin@sparepro.local", "Admin@12345")

    res = client.get('/api/support-messages/1')
    assert res.status_code == 200
    json_data = res.get_json()
    assert json_data['success'] is True
    assert json_data['data']['name'] == "Rajesh Kumar"
    assert json_data['data']['subject'] == "Motor Bearing Query"


def test_admin_can_update_message_status(app_context):
    client = app_context.test_client()
    login(client, "admin@sparepro.local", "Admin@12345")

    res = client.put('/api/support-messages/1/status', json={'status': 'replied'})
    assert res.status_code == 200
    json_data = res.get_json()
    assert json_data['success'] is True
    assert json_data['data']['status'] == 'replied'

    # Verify persistence in database
    with app_context.app_context():
        msg = db.session.get(ContactMessage, 1)
        assert msg.status == 'replied'
        assert msg.name == "Rajesh Kumar"  # Original details preserved


# ─────────────────────────────────────────────
# 2. MANAGER PERMISSIONS & OPERATIONS
# ─────────────────────────────────────────────

def test_manager_can_retrieve_list_and_update_status(app_context):
    client = app_context.test_client()
    login(client, "manager@sparepro.local", "Manager@12345")

    # List
    res_list = client.get('/api/support-messages')
    assert res_list.status_code == 200
    assert len(res_list.get_json()['data']) == 2

    # Detail
    res_detail = client.get('/api/support-messages/2')
    assert res_detail.status_code == 200
    assert res_detail.get_json()['data']['subject'] == "Pump Shaft Material"

    # Status update
    res_update = client.post('/api/support-messages/2/status', json={'status': 'closed'})
    assert res_update.status_code == 200
    assert res_update.get_json()['data']['status'] == 'closed'

    with app_context.app_context():
        msg = db.session.get(ContactMessage, 2)
        assert msg.status == 'closed'


# ─────────────────────────────────────────────
# 3. EMPLOYEE ACCESS RESTRICTION (403 FORBIDDEN)
# ─────────────────────────────────────────────

def test_employee_access_denied(app_context):
    client = app_context.test_client()
    login(client, "employee@sparepro.local", "Employee@12345")

    res_list = client.get('/api/support-messages')
    assert res_list.status_code == 403
    assert res_list.get_json()['success'] is False

    res_detail = client.get('/api/support-messages/1')
    assert res_detail.status_code == 403

    res_update = client.put('/api/support-messages/1/status', json={'status': 'closed'})
    assert res_update.status_code == 403


# ─────────────────────────────────────────────
# 4. UNAUTHENTICATED ACCESS REJECTION (401 UNAUTHORIZED)
# ─────────────────────────────────────────────

def test_unauthenticated_access_rejected(app_context):
    client = app_context.test_client()

    res_list = client.get('/api/support-messages')
    assert res_list.status_code == 401
    assert res_list.get_json()['success'] is False

    res_detail = client.get('/api/support-messages/1')
    assert res_detail.status_code == 401

    res_update = client.put('/api/support-messages/1/status', json={'status': 'read'})
    assert res_update.status_code == 401


# ─────────────────────────────────────────────
# 5. ERROR HANDLING (404 NOT FOUND & 400 BAD REQUEST)
# ─────────────────────────────────────────────

def test_invalid_message_id_returns_404(app_context):
    client = app_context.test_client()
    login(client, "admin@sparepro.local", "Admin@12345")

    res = client.get('/api/support-messages/9999')
    assert res.status_code == 404
    assert res.get_json()['success'] is False
    assert b'not found' in res.data.lower()


def test_invalid_status_value_returns_400(app_context):
    client = app_context.test_client()
    login(client, "admin@sparepro.local", "Admin@12345")

    res = client.put('/api/support-messages/1/status', json={'status': 'invalid_status_code'})
    assert res.status_code == 400
    json_data = res.get_json()
    assert json_data['success'] is False
    assert 'Invalid status value' in json_data['message']

    # Confirm message status was NOT changed in DB
    with app_context.app_context():
        msg = db.session.get(ContactMessage, 1)
        assert msg.status == 'unread'


# ─────────────────────────────────────────────
# 6. SEARCH & FILTERING
# ─────────────────────────────────────────────

def test_search_and_status_filtering(app_context):
    client = app_context.test_client()
    login(client, "admin@sparepro.local", "Admin@12345")

    # Filter by status='read'
    res_filter = client.get('/api/support-messages?status=read')
    assert res_filter.status_code == 200
    data = res_filter.get_json()['data']
    assert len(data) == 1
    assert data[0]['name'] == "Suresh Patel"

    # Search query='Bearing'
    res_search = client.get('/api/support-messages?q=Bearing')
    assert res_search.status_code == 200
    data_search = res_search.get_json()['data']
    assert len(data_search) == 1
    assert data_search[0]['name'] == "Rajesh Kumar"

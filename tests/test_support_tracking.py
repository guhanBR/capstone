import pytest
from app import create_app, db
from app.models.user import User
from app.models.contact_message import ContactMessage
from app.models.contact_reply import ContactReply

@pytest.fixture
def app_context():
    app = create_app('testing')
    with app.app_context():
        db.create_all()

        # Customer 1
        cust1 = User(name="Anand Kumar", email="anand@example.com", phone="9876543210", role="customer", status="active")
        cust1.set_password("Customer@123")

        # Customer 2
        cust2 = User(name="Bhavna Sharma", email="bhavna@example.com", phone="9876543211", role="customer", status="active")
        cust2.set_password("Customer@123")

        # Staff users
        admin = User(name="Test Admin", email="admin@sparepro.local", phone="9998887770", role="admin", status="active")
        admin.set_password("Admin@12345")

        manager = User(name="Test Manager", email="manager@sparepro.local", phone="9998887771", role="manager", status="active")
        manager.set_password("Manager@12345")

        employee = User(name="Test Employee", email="employee@sparepro.local", phone="9998887772", role="employee", status="active")
        employee.set_password("Employee@12345")

        db.session.add_all([cust1, cust2, admin, manager, employee])
        db.session.commit()

        # Add pre-existing complaint for cust1
        msg1 = ContactMessage(
            name="Anand Kumar",
            email="anand@example.com",
            phone="9876543210",
            subject="Motor Bearing Noise",
            message="My 5HP monoblock motor bearing makes grinding sound.",
            status="replied"
        )
        db.session.add(msg1)
        db.session.commit()

        reply1 = ContactReply(
            contact_message_id=msg1.id,
            staff_id=admin.id,
            recipient_email="anand@example.com",
            subject="Re: Motor Bearing Noise",
            reply_body="Please replace with SKF 6205-2Z deep groove ball bearing.",
            sending_status="Sent"
        )
        db.session.add(reply1)
        db.session.commit()

        # Add pre-existing complaint for cust2
        msg2 = ContactMessage(
            name="Bhavna Sharma",
            email="bhavna@example.com",
            phone="9876543211",
            subject="Pump Seal Leak",
            message="Water is leaking through mechanical seal area.",
            status="unread"
        )
        db.session.add(msg2)
        db.session.commit()

        yield app

        db.session.remove()
        db.drop_all()


def login(client, email, password):
    return client.post('/auth/login', data={'email': email, 'password': password}, follow_redirects=True)


def test_customer_complaint_submission_success_and_reference_number(app_context, monkeypatch):
    client = app_context.test_client()

    # Mock acknowledgement email failure (SMTP missing)
    def mock_ack_fail(recipient_email, complaint_ref, subject):
        return False, "SMTP configuration missing"

    monkeypatch.setattr("app.utils.email_helper.send_complaint_acknowledgement_email", mock_ack_fail)

    res = client.post('/contact/', data={
        'name': 'Anand Kumar',
        'email': 'anand@example.com',
        'phone': '9876543210',
        'subject': 'Submersible Cable Length',
        'message': 'Can I order a 50 meter flat submersible cable with waterproof joint?'
    }, follow_redirects=True)

    assert res.status_code == 200
    assert b'Thank you for contacting SparePro!' in res.data
    assert b'Reference Number:' in res.data
    assert b'SR-' in res.data

    with app_context.app_context():
        msgs = ContactMessage.query.filter_by(subject='Submersible Cable Length').all()
        assert len(msgs) == 1
        msg = msgs[0]
        assert msg.email == 'anand@example.com'
        assert msg.status == 'unread'


def test_customer_complaint_submission_with_smtp_acknowledgement(app_context, monkeypatch):
    client = app_context.test_client()

    def mock_ack_success(recipient_email, complaint_ref, subject):
        return True, "Acknowledgement email sent successfully."

    monkeypatch.setattr("app.utils.email_helper.send_complaint_acknowledgement_email", mock_ack_success)

    res = client.post('/contact/', data={
        'name': 'Anand Kumar',
        'email': 'anand@example.com',
        'phone': '9876543210',
        'subject': 'Impeller Shaft Size',
        'message': 'What is the inner diameter of Texmo 1HP impeller?'
    }, follow_redirects=True)

    assert res.status_code == 200
    assert b'Thank you for contacting SparePro!' in res.data
    assert b'acknowledgement email has been sent' in res.data


def test_customer_can_view_own_complaints_and_replies(app_context):
    client = app_context.test_client()
    login(client, "anand@example.com", "Customer@123")

    res = client.get('/customer/profile?section=support_requests')
    assert res.status_code == 200
    assert b'My Support Requests' in res.data
    assert b'Motor Bearing Noise' in res.data
    assert b'SKF 6205-2Z' in res.data # Staff reply text
    # Ensure cust1 cannot see cust2's complaint in UI
    assert b'Pump Seal Leak' not in res.data


def test_customer_cannot_access_other_customer_complaint_detail(app_context):
    client = app_context.test_client()
    login(client, "anand@example.com", "Customer@123")

    # Message 2 belongs to cust2 (bhavna@example.com)
    res = client.get('/customer/support-requests/2', headers={'Accept': 'application/json'})
    assert res.status_code == 403
    json_data = res.get_json()
    assert json_data['success'] is False
    assert 'Access denied' in json_data['message']


def test_employee_cannot_access_admin_support_messages(app_context):
    client = app_context.test_client()
    login(client, "employee@sparepro.local", "Employee@12345")

    res = client.get('/api/support-messages')
    assert res.status_code == 403

    res_page = client.get('/admin/support-messages')
    assert res_page.status_code == 403


def test_admin_and_manager_can_access_and_reply(app_context, monkeypatch):
    client = app_context.test_client()
    login(client, "manager@sparepro.local", "Manager@12345")

    def mock_send_email(recipient_email, subject, reply_body):
        return True, "Email sent successfully", "SMTP-MSG-888"

    monkeypatch.setattr("app.routes.api.send_support_reply_email", mock_send_email)

    # Manager replies to message 2
    res = client.post('/api/support-messages/2/reply', json={
        'subject': 'Re: Pump Seal Leak',
        'reply_body': 'Please replace with 19mm silicon carbide mechanical seal.'
    })

    assert res.status_code == 200
    assert res.get_json()['success'] is True

    # Verify status changed to replied
    with app_context.app_context():
        msg2 = db.session.get(ContactMessage, 2)
        assert msg2.status == 'replied'

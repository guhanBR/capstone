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

        # Admin user
        admin = User(name="Test Admin", email="admin@sparepro.local", phone="9998887770", role="admin", status="active")
        admin.set_password("Admin@12345")

        # Manager user
        manager = User(name="Test Manager", email="manager@sparepro.local", phone="9998887771", role="manager", status="active")
        manager.set_password("Manager@12345")

        # Employee user
        employee = User(name="Test Employee", email="employee@sparepro.local", phone="9998887772", role="employee", status="active")
        employee.set_password("Employee@12345")

        # Create contact enquiry
        msg = ContactMessage(
            name="Anish Sharma",
            email="anish.sharma@example.com",
            phone="9876543212",
            subject="Submersible Impeller Query",
            message="Do you have Noryl impellers for 4-inch borewell pump?",
            status="unread"
        )
        db.session.add_all([admin, manager, employee, msg])
        db.session.commit()

        yield app

        db.session.remove()
        db.drop_all()


def login(client, email, password):
    return client.post('/auth/login', data={'email': email, 'password': password}, follow_redirects=True)


def test_admin_reply_creation_and_history(app_context, monkeypatch):
    client = app_context.test_client()
    login(client, "admin@sparepro.local", "Admin@12345")

    # Mock send_support_reply_email to simulate successful SMTP submission
    def mock_send_email(recipient_email, subject, reply_body):
        return True, "Email sent successfully", "SMTP-MSG-12345"

    monkeypatch.setattr("app.routes.api.send_support_reply_email", mock_send_email)

    res = client.post('/api/support-messages/1/reply', json={
        'subject': 'Re: Submersible Impeller Query',
        'reply_body': 'Yes, we stock 4-inch Noryl stage impellers for Texmo submersibles.'
    })

    assert res.status_code == 200
    json_data = res.get_json()
    assert json_data['success'] is True
    assert json_data['data']['sending_status'] == 'Sent'
    assert json_data['data']['recipient_email'] == 'anish.sharma@example.com'

    # Verify DB persistence
    with app_context.app_context():
        replies = ContactReply.query.filter_by(contact_message_id=1).all()
        assert len(replies) == 1
        assert replies[0].reply_body == 'Yes, we stock 4-inch Noryl stage impellers for Texmo submersibles.'
        assert replies[0].sending_status == 'Sent'

        # Verify message status updated to replied
        msg = db.session.get(ContactMessage, 1)
        assert msg.status == 'replied'

    # Test retrieving reply history
    res_history = client.get('/api/support-messages/1/replies')
    assert res_history.status_code == 200
    h_data = res_history.get_json()['data']
    assert len(h_data) == 1
    assert h_data[0]['recipient_email'] == 'anish.sharma@example.com'


def test_manager_can_send_reply(app_context, monkeypatch):
    client = app_context.test_client()
    login(client, "manager@sparepro.local", "Manager@12345")

    def mock_send_email(recipient_email, subject, reply_body):
        return True, "Email sent", "SMTP-MSG-999"

    monkeypatch.setattr("app.routes.api.send_support_reply_email", mock_send_email)

    res = client.post('/api/support-messages/1/reply', json={
        'subject': 'Re: Submersible Impeller Query',
        'reply_body': 'Manager response details.'
    })
    assert res.status_code == 200
    assert res.get_json()['success'] is True


def test_employee_cannot_send_reply_or_view_history(app_context):
    client = app_context.test_client()
    login(client, "employee@sparepro.local", "Employee@12345")

    res_post = client.post('/api/support-messages/1/reply', json={
        'subject': 'Re: Test',
        'reply_body': 'Unauthorized reply'
    })
    assert res_post.status_code == 403

    res_get = client.get('/api/support-messages/1/replies')
    assert res_get.status_code == 403


def test_unauthenticated_cannot_send_reply(app_context):
    client = app_context.test_client()

    res = client.post('/api/support-messages/1/reply', json={
        'subject': 'Re: Test',
        'reply_body': 'Unauthenticated reply'
    })
    assert res.status_code == 401


def test_empty_reply_body_rejected(app_context):
    client = app_context.test_client()
    login(client, "admin@sparepro.local", "Admin@12345")

    res = client.post('/api/support-messages/1/reply', json={
        'subject': 'Re: Test',
        'reply_body': '' # Empty body
    })
    assert res.status_code == 400
    assert res.get_json()['success'] is False


def test_smtp_failure_handling_and_status_recording(app_context, monkeypatch):
    client = app_context.test_client()
    login(client, "admin@sparepro.local", "Admin@12345")

    # Simulate SMTP failure (e.g. missing credentials or connection timeout)
    def mock_send_email_fail(recipient_email, subject, reply_body):
        return False, "SMTP configuration missing: MAIL_USERNAME and MAIL_PASSWORD environment variables are not set.", None

    monkeypatch.setattr("app.routes.api.send_support_reply_email", mock_send_email_fail)

    res = client.post('/api/support-messages/1/reply', json={
        'subject': 'Re: Submersible Impeller Query',
        'reply_body': 'Test response with missing SMTP config.'
    })

    assert res.status_code == 400
    json_data = res.get_json()
    assert json_data['success'] is False
    assert 'SMTP configuration missing' in json_data['message']

    # Verify record saved with status 'Failed' in database
    with app_context.app_context():
        replies = ContactReply.query.filter_by(contact_message_id=1).all()
        assert len(replies) == 1
        assert replies[0].sending_status == 'Failed'
        assert 'SMTP configuration missing' in replies[0].error_message

import pytest
from unittest.mock import MagicMock, patch
from app import create_app, db
from app.models.user import User
from app.models.contact_message import ContactMessage
from app.models.contact_reply import ContactReply
from app.utils.email_helper import send_support_reply_email, send_complaint_acknowledgement_email


@pytest.fixture
def app_context():
    app = create_app('testing')
    with app.app_context():
        db.create_all()

        admin = User(name="Test Admin", email="admin@sparepro.local", phone="9998887770", role="admin", status="active")
        admin.set_password("Admin@12345")

        msg = ContactMessage(
            name="Ramesh Gupta",
            email="ramesh@example.com",
            phone="9876543210",
            subject="Submersible Motor Starter Query",
            message="Which DOL starter is suitable for 3HP single phase motor?",
            status="unread"
        )
        db.session.add_all([admin, msg])
        db.session.commit()

        yield app

        db.session.remove()
        db.drop_all()


def test_missing_credentials_returns_clear_error(app_context):
    """Test that missing MAIL_USERNAME or MAIL_PASSWORD produces an explicit error without attempting connection."""
    app_context.config['MAIL_USERNAME'] = ''
    app_context.config['MAIL_PASSWORD'] = ''

    success, msg, provider_id = send_support_reply_email("customer@example.com", "Test Subject", "Test Body")
    assert success is False
    assert "SMTP configuration missing: MAIL_USERNAME and MAIL_PASSWORD environment variables are not set." in msg
    assert provider_id is None

    ack_success, ack_msg = send_complaint_acknowledgement_email("customer@example.com", "SR-0001", "Test Subject")
    assert ack_success is False
    assert "SMTP configuration missing: MAIL_USERNAME and MAIL_PASSWORD environment variables are not set." in ack_msg


def test_whitespace_credentials_handled_as_missing(app_context):
    """Test that whitespace-only credentials are treated as missing."""
    app_context.config['MAIL_USERNAME'] = '   '
    app_context.config['MAIL_PASSWORD'] = '   '

    success, msg, _ = send_support_reply_email("customer@example.com", "Test Subject", "Test Body")
    assert success is False
    assert "SMTP configuration missing" in msg


def test_smtp_tls_connection_and_send(app_context):
    """Test standard TLS SMTP sending path using mock smtplib.SMTP."""
    app_context.config['MAIL_SERVER'] = 'smtp.testprovider.com'
    app_context.config['MAIL_PORT'] = 587
    app_context.config['MAIL_USE_TLS'] = True
    app_context.config['MAIL_USE_SSL'] = False
    app_context.config['MAIL_USERNAME'] = 'test_user@sparepro.com'
    app_context.config['MAIL_PASSWORD'] = 'secret_app_password'

    with patch('smtplib.SMTP') as mock_smtp_cls:
        mock_server = MagicMock()
        mock_smtp_cls.return_value = mock_server

        success, msg, provider_id = send_support_reply_email("customer@example.com", "Subject", "Body text")

        assert success is True
        assert "submitted successfully" in msg
        assert provider_id == "SMTP-customer@example.com"

        mock_smtp_cls.assert_called_once_with('smtp.testprovider.com', 587, timeout=10)
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once_with('test_user@sparepro.com', 'secret_app_password')
        mock_server.send_message.assert_called_once()
        mock_server.quit.assert_called_once()


def test_smtp_ssl_connection_and_send(app_context):
    """Test SSL (Port 465) SMTP sending path using mock smtplib.SMTP_SSL."""
    app_context.config['MAIL_SERVER'] = 'smtp.testprovider.com'
    app_context.config['MAIL_PORT'] = 465
    app_context.config['MAIL_USE_TLS'] = False
    app_context.config['MAIL_USE_SSL'] = True
    app_context.config['MAIL_USERNAME'] = 'test_user@sparepro.com'
    app_context.config['MAIL_PASSWORD'] = 'secret_app_password'

    with patch('smtplib.SMTP_SSL') as mock_smtp_ssl_cls:
        mock_server = MagicMock()
        mock_smtp_ssl_cls.return_value = mock_server

        success, msg, provider_id = send_support_reply_email("customer@example.com", "Subject", "Body text")

        assert success is True
        assert "submitted successfully" in msg
        mock_smtp_ssl_cls.assert_called_once_with('smtp.testprovider.com', 465, timeout=10)
        mock_server.login.assert_called_once_with('test_user@sparepro.com', 'secret_app_password')
        mock_server.send_message.assert_called_once()
        mock_server.quit.assert_called_once()


def test_smtp_auth_failure_error_handling(app_context):
    """Test that SMTP authentication failure is caught cleanly without exposing secrets."""
    import smtplib
    app_context.config['MAIL_USERNAME'] = 'test_user@sparepro.com'
    app_context.config['MAIL_PASSWORD'] = 'invalid_password'

    with patch('smtplib.SMTP') as mock_smtp_cls:
        mock_server = MagicMock()
        mock_server.login.side_effect = smtplib.SMTPAuthenticationError(535, b"5.7.8 Authentication failed")
        mock_smtp_cls.return_value = mock_server

        success, msg, provider_id = send_support_reply_email("customer@example.com", "Subject", "Body text")

        assert success is False
        assert "SMTP delivery failed" in msg
        assert "535" in msg
        # Ensure password is NOT leaked in message
        assert "invalid_password" not in msg


def test_api_support_reply_records_failure_in_db(app_context):
    """Test that API endpoint creates pending reply, records failure on SMTP error, and returns 400."""
    client = app_context.test_client()
    client.post('/auth/login', data={'email': 'admin@sparepro.local', 'password': 'Admin@12345'})

    with patch('app.routes.api.send_support_reply_email') as mock_send:
        mock_send.return_value = (False, "SMTP configuration missing: MAIL_USERNAME and MAIL_PASSWORD environment variables are not set.", None)

        res = client.post('/api/support-messages/1/reply', json={
            'subject': 'Re: Submersible Motor Starter Query',
            'reply_body': 'We recommend 3HP BCH or L&T DOL starter.'
        })

        assert res.status_code == 400
        json_data = res.get_json()
        assert json_data['success'] is False
        assert 'SMTP configuration missing' in json_data['message']

    with app_context.app_context():
        replies = ContactReply.query.filter_by(contact_message_id=1).all()
        assert len(replies) == 1
        assert replies[0].sending_status == 'Failed'
        assert 'SMTP configuration missing' in replies[0].error_message

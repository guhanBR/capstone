import pytest
from app import create_app, db
from app.models.user import User

@pytest.fixture
def app():
    app = create_app('testing')
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()

def test_user_registration(client):
    response = client.post('/auth/register', data={
        'name': 'Test User',
        'email': 'testuser@example.com',
        'phone': '9876543210',
        'password': 'Password123',
        'confirm_password': 'Password123'
    }, follow_redirects=True)

    assert response.status_code == 200
    user = User.query.filter_by(email='testuser@example.com').first()
    assert user is not None
    assert user.name == 'Test User'
    assert user.role == 'customer'

def test_invalid_login(client):
    response = client.post('/auth/login', data={
        'email': 'nonexistent@example.com',
        'password': 'WrongPassword'
    }, follow_redirects=True)

    assert b'Invalid email or password' in response.data

def test_admin_authorization_guard(client, app):
    # Customer user attempting to access admin route
    with app.app_context():
        u = User(name="Cust", email="c@ex.com", phone="9876543210", role="customer")
        u.set_password("pass123")
        db.session.add(u)
        db.session.commit()

    client.post('/auth/login', data={'email': 'c@ex.com', 'password': 'pass123'})
    res = client.get('/admin/dashboard')
    assert res.status_code == 403

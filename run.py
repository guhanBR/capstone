import os
from app import create_app, db

env = os.environ.get('FLASK_ENV', 'development')
app = create_app(env)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    print("=" * 65)
    print(" SparePro -- Motors and Pumps Spare Parts System Running!")
    print(" Application URL: http://127.0.0.1:5000")
    print(" Admin Login   : admin@sparepro.local / Admin@12345")
    print(" Customer Login: rajesh.kumar@example.com / Customer@123")
    print("=" * 65)
    app.run(host='0.0.0.0', port=5000, debug=True)

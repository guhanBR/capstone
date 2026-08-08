from app import db
from app.models.user import User
from app.models.cart import Cart
from app.utils.validators import validate_email, validate_phone, validate_password

class AuthService:
    @staticmethod
    def register_user(name, email, phone, password, role='customer'):
        # Validate email format
        valid_email, msg = validate_email(email)
        if not valid_email:
            return False, msg, None

        # Validate phone
        valid_phone, msg = validate_phone(phone)
        if not valid_phone:
            return False, msg, None

        # Validate password
        valid_pass, msg = validate_password(password)
        if not valid_pass:
            return False, msg, None

        # Check existing email
        existing_user = User.query.filter_by(email=email.lower().strip()).first()
        if existing_user:
            return False, "An account with this email address already exists.", None

        try:
            user = User(
                name=name.strip(),
                email=email.lower().strip(),
                phone=phone.strip(),
                role=role,
                status='active'
            )
            user.set_password(password)
            db.session.add(user)
            db.session.flush()

            # Create empty cart for customer
            if role == 'customer':
                cart = Cart(user_id=user.id)
                db.session.add(cart)

            db.session.commit()
            return True, "Registration successful!", user
        except Exception as e:
            db.session.rollback()
            return False, f"An error occurred during registration: {str(e)}", None

    @staticmethod
    def authenticate_user(email, password):
        if not email or not password:
            return False, "Email and password are required.", None

        user = User.query.filter_by(email=email.lower().strip()).first()
        if not user or not user.check_password(password):
            return False, "Invalid email or password.", None

        if user.status != 'active':
            return False, "Your account has been deactivated. Please contact support.", None

        return True, "Login successful!", user

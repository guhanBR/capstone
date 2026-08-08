from datetime import datetime, timezone
import random
from app import db
from app.models.audit_log import AuditLog

def generate_order_number():
    """Generates order numbers in SP-YYYYMMDD-XXXX format"""
    date_str = datetime.now(timezone.utc).strftime('%Y%m%d')
    random_digits = f"{random.randint(1000, 9999)}"
    return f"SP-{date_str}-{random_digits}"

def format_currency(amount):
    """Formats float/numeric amount to INR currency format"""
    if amount is None:
        return "₹0.00"
    return f"₹{float(amount):,.2f}"

def log_audit(user_id, action, entity_type, entity_id=None, description=None):
    """Logs an administrative or critical operation into audit_logs"""
    try:
        log_entry = AuditLog(
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            description=description
        )
        db.session.add(log_entry)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"Error creating audit log: {e}")

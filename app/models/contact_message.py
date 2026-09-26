from datetime import datetime, timezone
from app import db

class ContactMessage(db.Model):
    __tablename__ = 'contact_messages'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(20), nullable=True)
    subject = db.Column(db.String(150), nullable=False)
    message = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='unread', nullable=False)  # unread, read, in_progress, replied, closed
    is_read = db.Column(db.Boolean, default=False, nullable=False)
    read_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'phone': self.phone,
            'subject': self.subject,
            'message': self.message,
            'status': self.status,
            'is_read': self.is_read,
            'read_at': self.read_at.strftime('%Y-%m-%d %H:%M:%S') if self.read_at else None,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None
        }

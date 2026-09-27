from datetime import datetime, timezone
from app import db

class ContactReply(db.Model):
    __tablename__ = 'support_replies'

    id = db.Column(db.Integer, primary_key=True)
    contact_message_id = db.Column(db.Integer, db.ForeignKey('contact_messages.id', ondelete='CASCADE'), nullable=False)
    staff_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    recipient_email = db.Column(db.String(120), nullable=False)
    subject = db.Column(db.String(200), nullable=False)
    reply_body = db.Column(db.Text, nullable=False)
    sending_status = db.Column(db.String(20), nullable=False, default='Pending') # Pending, Sent, Failed
    error_message = db.Column(db.Text, nullable=True)
    provider_message_id = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    contact_message = db.relationship('ContactMessage', backref=db.backref('replies', lazy=True, cascade='all, delete-orphan'))
    staff_user = db.relationship('User', backref=db.backref('support_replies', lazy=True))

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def to_dict(self):
        return {
            'id': self.id,
            'contact_message_id': self.contact_message_id,
            'staff_id': self.staff_id,
            'staff_name': self.staff_user.name if self.staff_user else 'System Staff',
            'recipient_email': self.recipient_email,
            'subject': self.subject,
            'reply_body': self.reply_body,
            'sending_status': self.sending_status,
            'error_message': self.error_message,
            'provider_message_id': self.provider_message_id,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None
        }

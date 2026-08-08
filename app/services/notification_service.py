from app import db
from app.models.notification import Notification

class NotificationService:
    @staticmethod
    def send_notification(user_id, title, message, notif_type='info'):
        try:
            notif = Notification(
                user_id=user_id,
                title=title,
                message=message,
                type=notif_type
            )
            db.session.add(notif)
            db.session.commit()
            return True
        except Exception as e:
            db.session.rollback()
            return False

    @staticmethod
    def mark_as_read(notif_id, user_id):
        notif = db.session.get(Notification, notif_id)
        if notif and notif.user_id == user_id:
            notif.is_read = True
            db.session.commit()
            return True
        return False

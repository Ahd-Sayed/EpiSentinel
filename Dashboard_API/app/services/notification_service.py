from app.extensions import db
from app.models.notification import Notification

class NotificationService:
    @staticmethod
    def add_notification(title, message, category="Information"):
        """Create a new notification entry."""
        n = Notification(
            title=title,
            message=message,
            category=category
        )
        db.session.add(n)
        db.session.commit()
        return n

    @staticmethod
    def get_notifications(limit=50, only_unread=False):
        """Retrieve notifications log list."""
        query = Notification.query
        if only_unread:
            query = query.filter_by(is_read=False)
        return query.order_by(Notification.created_at.desc()).limit(limit).all()

    @staticmethod
    def get_unread_count():
        """Retrieve number of unread notifications."""
        return Notification.query.filter_by(is_read=False).count()

    @staticmethod
    def mark_as_read(notification_id):
        """Mark a single notification as read."""
        n = Notification.query.get(notification_id)
        if n:
            n.is_read = True
            db.session.commit()
            return True
        return False

    @staticmethod
    def mark_all_as_read():
        """Mark all notifications as read."""
        Notification.query.filter_by(is_read=False).update({Notification.is_read: True})
        db.session.commit()
        return True

    @staticmethod
    def delete_notification(notification_id):
        """Delete a notification."""
        n = Notification.query.get(notification_id)
        if n:
            db.session.delete(n)
            db.session.commit()
            return True
        return False

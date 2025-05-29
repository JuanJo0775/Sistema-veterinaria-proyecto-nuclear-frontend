# microservices/notification_service/app/models/__init__.py
from .notification import Notification, db

__all__ = ['Notification', 'db']
"""
Simple notification system for real-time alerts.
Stores notifications in-memory and serves them via API.
"""

from collections import deque
from datetime import datetime
from django.utils import timezone

# In-memory notification queue (max 100 notifications)
notifications_queue = deque(maxlen=100)


class NotificationService:
    """Service for managing real-time notifications"""
    
    @staticmethod
    def add_notification(title: str, message: str, notification_type: str = 'info', auto_dismiss: int = 5000):
        """
        Add a notification to the queue.
        
        Args:
            title: Notification title
            message: Notification message
            notification_type: 'success', 'error', 'warning', 'info'
            auto_dismiss: Auto-dismiss time in milliseconds (0 = manual)
        """
        notification = {
            'id': len(notifications_queue),
            'title': title,
            'message': message,
            'type': notification_type,
            'timestamp': timezone.now().isoformat(),
            'auto_dismiss': auto_dismiss,
        }
        notifications_queue.append(notification)
    
    @staticmethod
    def get_all_notifications():
        """Get all pending notifications"""
        return list(notifications_queue)
    
    @staticmethod
    def clear_notifications():
        """Clear all notifications"""
        notifications_queue.clear()
    
    # Convenience methods for different notification types
    @staticmethod
    def success(title: str, message: str):
        """Send success notification"""
        NotificationService.add_notification(title, message, 'success', 5000)
    
    @staticmethod
    def error(title: str, message: str):
        """Send error notification"""
        NotificationService.add_notification(title, message, 'error', 7000)
    
    @staticmethod
    def warning(title: str, message: str):
        """Send warning notification"""
        NotificationService.add_notification(title, message, 'warning', 6000)
    
    @staticmethod
    def info(title: str, message: str):
        """Send info notification"""
        NotificationService.add_notification(title, message, 'info', 5000)

"""
Notification API endpoint for real-time alerts.
"""

from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from .notifications import NotificationService


class NotificationsView(APIView):
    """
    Get all pending notifications.
    
    GET /api/notifications/
    
    Response:
    {
        "notifications": [
            {
                "id": 0,
                "title": "Incident Triggered",
                "message": "Service: database",
                "type": "warning",
                "timestamp": "2025-12-28T...",
                "auto_dismiss": 5000
            }
        ]
    }
    """
    
    def get(self, request):
        """Get all pending notifications and clear them (prevents repeats on reload)"""
        notifications = NotificationService.get_all_notifications()
        # Clear notifications after fetching so they don't repeat on page reload
        NotificationService.clear_notifications()
        return Response({
            'notifications': notifications,
            'count': len(notifications)
        }, status=status.HTTP_200_OK)
    
    def delete(self, request):
        """Clear all notifications"""
        NotificationService.clear_notifications()
        return Response({
            'status': 'All notifications cleared'
        }, status=status.HTTP_200_OK)

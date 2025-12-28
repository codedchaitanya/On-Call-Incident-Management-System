from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    # Legacy endpoints
    UserCreateView, UserListView, UserUpdateView, UserDeleteView,
    IncidentCreateView, IncidentListView, IncidentUpdateView,
    IncidentDeleteView, IncidentSearchView, GetInfofromPin,
    # New on-call incident management endpoints
    IncidentTriggerView, IncidentAcknowledgeView, IncidentResolveView,
    IncidentEscalateView, EscalationCheckView, OnCallScheduleViewSet,
    EscalationLevelViewSet, MetricsView, IncidentListDetailView
)
from .notifications_views import NotificationsView

# Create router for viewsets
router = DefaultRouter()
router.register(r'oncall/schedules', OnCallScheduleViewSet, basename='oncall-schedule')
router.register(r'escalation/levels', EscalationLevelViewSet, basename='escalation-level')

urlpatterns = [
    # Router URLs
    path('', include(router.urls)),
    
    # Legacy endpoints (backward compatibility)
    path('users/register/', UserCreateView.as_view(), name='user-create'),
    path('users/', UserListView.as_view(), name='user-list'),
    path('users/update/', UserUpdateView.as_view(), name='user-update'),
    path('users/delete/', UserDeleteView.as_view(), name='user-delete'),
    path('incidents/create/', IncidentCreateView.as_view(), name='incident-create'),
    path('incidents/legacy/', IncidentListView.as_view(), name='incident-list-legacy'),
    path('incidents/update/', IncidentUpdateView.as_view(), name='incident-update'),
    path('incidents/delete/', IncidentDeleteView.as_view(), name='incident-delete'),
    path('incidents/search/', IncidentSearchView.as_view(), name='incident-search'),
    path('pincode/<str:pincode>/', GetInfofromPin.as_view(), name='get-pincode-info'),
    
    # New on-call incident management endpoints
    path('incidents/trigger/', IncidentTriggerView.as_view(), name='incident-trigger'),
    path('incidents/<int:id>/acknowledge/', IncidentAcknowledgeView.as_view(), name='incident-acknowledge'),
    path('incidents/<int:id>/resolve/', IncidentResolveView.as_view(), name='incident-resolve'),
    path('incidents/<int:id>/escalate/', IncidentEscalateView.as_view(), name='incident-escalate'),
    path('incidents/escalate/check/', EscalationCheckView.as_view(), name='escalation-check'),
    path('incidents/list/all/', IncidentListDetailView.as_view(), name='incident-list-all'),
    
    # Metrics endpoint
    path('metrics/', MetricsView.as_view(), name='metrics'),
    
    # Notifications endpoint
    path('notifications/', NotificationsView.as_view(), name='notifications'),
]

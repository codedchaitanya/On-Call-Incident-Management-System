"""
Business logic layer for incident management.
Handles complex operations like on-call lookups, incident state transitions, and escalations.
"""

from django.utils import timezone
from django.db.models import Q
from datetime import timedelta
from .models import OnCallSchedule, Incident, EscalationLevel
from django.contrib.auth.models import User as DjangoUser
from .notifications import NotificationService
import logging

logger = logging.getLogger(__name__)


class OnCallService:
    """Service for managing on-call schedules and lookups"""
    
    @staticmethod
    def get_on_call_user(service_name: str, current_time=None):
        """
        Determine the on-call user for a given service at a specific time.
        
        Logic:
        1. Filter schedules by service_name
        2. Find schedules where: start_time <= current_time <= end_time
        3. Prioritize: overrides > regular schedules, then earliest created
        4. Return user or None if not found
        
        Args:
            service_name: Name of the service
            current_time: DateTime to check (defaults to now)
        
        Returns:
            DjangoUser object or None
        """
        if current_time is None:
            current_time = timezone.now()
        
        # Get all active schedules at this time, prioritizing overrides
        schedules = OnCallSchedule.objects.filter(
            service_name=service_name,
            start_time__lte=current_time,
            end_time__gte=current_time
        ).order_by('-is_override', 'created_at')
        
        if schedules.exists():
            return schedules.first().user
        
        return None
    
    @staticmethod
    def get_all_active_schedules(service_name: str, current_time=None):
        """Get all active schedules for a service (for debugging/monitoring)"""
        if current_time is None:
            current_time = timezone.now()
        
        return OnCallSchedule.objects.filter(
            service_name=service_name,
            start_time__lte=current_time,
            end_time__gte=current_time
        ).order_by('-is_override', 'created_at')
    
    @staticmethod
    def create_schedule(user, service_name, start_time, end_time, is_override=False):
        """Create a new on-call schedule"""
        schedule = OnCallSchedule.objects.create(
            user=user,
            service_name=service_name,
            start_time=start_time,
            end_time=end_time,
            is_override=is_override
        )
        logger.info(f"[SCHEDULE] Created {service_name} schedule for {user.username} "
                   f"({start_time} - {end_time}). Override: {is_override}")
        return schedule


class IncidentService:
    """Service for managing incident lifecycle"""
    
    # Configuration
    ESCALATION_TIMEOUT = 5 * 60  # 5 minutes in seconds
    DEDUPLICATION_WINDOW = 5 * 60  # 5 minutes in seconds
    
    @staticmethod
    def create_incident(title: str, description: str, service_name: str, 
                       auto_assign=True, deduplication_enabled=True):
        """
        Create a new incident and automatically assign to on-call user.
        
        Args:
            title: Incident title
            description: Incident description
            service_name: Name of affected service
            auto_assign: Whether to automatically assign to on-call user
            deduplication_enabled: Whether to check for duplicate incidents
        
        Returns:
            Incident object
        """
        # Check for duplicate incidents
        if deduplication_enabled:
            duplicate = IncidentService.find_duplicate_incident(
                service_name, title
            )
            if duplicate:
                logger.info(f"[DEDUP] Found duplicate incident {duplicate.id} "
                           f"for {service_name}:{title}")
                NotificationService.info(
                    "Duplicate Detected",
                    f"Incident #{duplicate.id} already exists for {title}"
                )
                return duplicate
        
        # Create incident
        incident = Incident.objects.create(
            title=title,
            description=description,
            service_name=service_name,
            status=Incident.STATUS_TRIGGERED
        )
        
        # Auto-assign to on-call user
        if auto_assign:
            on_call_user = OnCallService.get_on_call_user(service_name)
            if on_call_user:
                incident.assigned_to = on_call_user
                incident.save()
                logger.info(f"[ASSIGNED] Incident {incident.id} assigned to {on_call_user.username}")
            else:
                logger.warning(f"[NO_ONCALL] No on-call user found for {service_name}")
                NotificationService.warning(
                    "⚠️ No On-Call User",
                    f"No on-call user found for {service_name}. Incident {incident.id} remains UNASSIGNED."
                )
        
        # Send notification
        assigned_user = incident.assigned_to.username if incident.assigned_to else "UNASSIGNED"
        print(f"\n🚨 ALERT 🚨")
        print(f"Service: {service_name}")
        print(f"Incident: {title}")
        print(f"Incident ID: {incident.id}")
        print(f"Assigned To: {assigned_user}")
        print(f"Description: {description}\n")
        
        NotificationService.warning(
            "🚨 Incident Triggered",
            f"Service: {service_name} | Assigned To: {assigned_user}"
        )
        
        return incident
    
    @staticmethod
    def find_duplicate_incident(service_name: str, title: str, time_window=None):
        """
        Find a duplicate incident within the deduplication window.
        
        Duplicate = same service_name + title within last X minutes in TRIGGERED state
        """
        if time_window is None:
            time_window = IncidentService.DEDUPLICATION_WINDOW
        
        cutoff_time = timezone.now() - timedelta(seconds=time_window)
        
        duplicate = Incident.objects.filter(
            service_name=service_name,
            title=title,
            status=Incident.STATUS_TRIGGERED,
            created_at__gte=cutoff_time
        ).first()
        
        return duplicate
    
    @staticmethod
    def acknowledge_incident(incident_id: int):
        """
        Acknowledge an incident.
        
        Transitions: TRIGGERED -> ACKNOWLEDGED
        """
        try:
            incident = Incident.objects.get(id=incident_id)
        except Incident.DoesNotExist:
            raise ValueError(f"Incident {incident_id} not found")
        
        # Check if incident is acknowledgeable
        if not incident.is_acknowledgeable:
            raise ValueError(
                f"Cannot acknowledge incident in {incident.status} state. "
                f"Expected: {Incident.STATUS_TRIGGERED}"
            )
        
        incident.status = Incident.STATUS_ACKNOWLEDGED
        incident.acknowledged_at = timezone.now()
        incident.save()
        
        assigned_user = incident.assigned_to.username if incident.assigned_to else "Unknown"
        print(f"\n✅ Incident {incident.id} acknowledged by {assigned_user}\n")
        logger.info(f"[ACKNOWLEDGED] Incident {incident.id} by {assigned_user}")
        
        NotificationService.success(
            "✅ Incident Acknowledged",
            f"Incident #{incident.id} acknowledged by {assigned_user}"
        )
        
        return incident
    
    @staticmethod
    def resolve_incident(incident_id: int):
        """
        Resolve an incident.
        
        Transitions: ACKNOWLEDGED -> RESOLVED
        """
        try:
            incident = Incident.objects.get(id=incident_id)
        except Incident.DoesNotExist:
            raise ValueError(f"Incident {incident_id} not found")
        
        # Check if incident is resolvable
        if not incident.is_resolvable:
            raise ValueError(
                f"Cannot resolve incident in {incident.status} state. "
                f"Expected: {Incident.STATUS_ACKNOWLEDGED}"
            )
        
        incident.status = Incident.STATUS_RESOLVED
        incident.resolved_at = timezone.now()
        incident.save()
        
        print(f"\n✅ Incident {incident.id} resolved\n")
        logger.info(f"[RESOLVED] Incident {incident.id}")
        
        NotificationService.success(
            "✅ Incident Resolved",
            f"Incident #{incident.id} has been resolved"
        )
        
        return incident
    
    @staticmethod
    def escalate_incident(incident_id: int):
        """
        Escalate an incident to the next level.
        
        Transitions: TRIGGERED -> ESCALATED
        Sends escalation notification (notification channel independent of users)
        """
        try:
            incident = Incident.objects.get(id=incident_id)
        except Incident.DoesNotExist:
            raise ValueError(f"Incident {incident_id} not found")
        
        # Check if incident can be escalated
        if not incident.can_escalate:
            raise ValueError(
                f"Cannot escalate incident in {incident.status} state. "
                f"Expected: {Incident.STATUS_TRIGGERED}"
            )
        
        # Find escalation path for this service
        escalation_levels = EscalationLevel.objects.filter(
            service_name=incident.service_name
        ).order_by('level')
        
        if not escalation_levels.exists():
            raise ValueError(f"No escalation path defined for {incident.service_name}")
        
        # Get first escalation level
        escalation_level = escalation_levels.first()
        
        incident.status = Incident.STATUS_ESCALATED
        incident.escalated_at = timezone.now()
        incident.save()
        
        print(f"\n⚠️ INCIDENT ESCALATED")
        print(f"Incident ID: {incident.id}")
        print(f"Service: {incident.service_name}")
        print(f"Notify Level {escalation_level.level}: {escalation_level.notification_channel}\n")
        logger.warning(f"[ESCALATED] Incident {incident.id} to Level {escalation_level.level} "
                      f"({escalation_level.notification_channel})")
        
        NotificationService.error(
            "⚠️ Incident Escalated",
            f"Incident #{incident.id} escalated to Level {escalation_level.level}"
        )
        
        return incident
    
    @staticmethod
    def check_escalations(timeout_seconds=None):
        """
        Check all triggered incidents and escalate those that exceed timeout.
        
        Should be run periodically (e.g., via management command).
        """
        if timeout_seconds is None:
            timeout_seconds = IncidentService.ESCALATION_TIMEOUT
        
        cutoff_time = timezone.now() - timedelta(seconds=timeout_seconds)
        
        # Find incidents that should be escalated
        incidents_to_escalate = Incident.objects.filter(
            status=Incident.STATUS_TRIGGERED,
            created_at__lt=cutoff_time
        )
        
        escalated_count = 0
        for incident in incidents_to_escalate:
            try:
                IncidentService.escalate_incident(incident.id)
                escalated_count += 1
            except ValueError as e:
                error_msg = str(e)
                logger.error(f"Failed to escalate incident {incident.id}: {e}")
                NotificationService.error(
                    "❌ Escalation Failed",
                    f"Failed to escalate incident {incident.id}: {error_msg}"
                )
        
        if escalated_count > 0:
            logger.info(f"[ESCALATION_CHECK] Escalated {escalated_count} incidents")
        
        return escalated_count


class MetricsService:
    """Service for calculating incident metrics"""
    
    @staticmethod
    def calculate_mtta(incident):
        """Mean Time To Acknowledge"""
        if incident.acknowledged_at and incident.created_at:
            delta = incident.acknowledged_at - incident.created_at
            return delta.total_seconds() / 60  # Return in minutes
        return None
    
    @staticmethod
    def calculate_mttr(incident):
        """Mean Time To Resolve"""
        if incident.resolved_at and incident.created_at:
            delta = incident.resolved_at - incident.created_at
            return delta.total_seconds() / 60  # Return in minutes
        return None
    
    @staticmethod
    def get_metrics(service_name=None, start_date=None, end_date=None):
        """
        Calculate aggregate metrics for incidents.
        
        Returns:
            Dictionary with MTTA, MTTR, total incidents, resolved count
        """
        queryset = Incident.objects.filter(status=Incident.STATUS_RESOLVED)
        
        if service_name:
            queryset = queryset.filter(service_name=service_name)
        
        if start_date:
            queryset = queryset.filter(created_at__gte=start_date)
        
        if end_date:
            queryset = queryset.filter(created_at__lte=end_date)
        
        incidents = list(queryset)
        
        if not incidents:
            return {
                'mtta_minutes': None,
                'mttr_minutes': None,
                'total_incidents': 0,
                'resolved_count': 0,
                'avg_response_time': None,
            }
        
        mtta_values = [
            MetricsService.calculate_mtta(i) for i in incidents 
            if MetricsService.calculate_mtta(i) is not None
        ]
        mttr_values = [
            MetricsService.calculate_mttr(i) for i in incidents 
            if MetricsService.calculate_mttr(i) is not None
        ]
        
        return {
            'mtta_minutes': sum(mtta_values) / len(mtta_values) if mtta_values else None,
            'mttr_minutes': sum(mttr_values) / len(mttr_values) if mttr_values else None,
            'total_incidents': len(incidents),
            'resolved_count': len(incidents),
            'avg_response_time': sum(mtta_values) / len(mtta_values) if mtta_values else None,
        }

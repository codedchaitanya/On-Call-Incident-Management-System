from django.test import TestCase
from django.utils import timezone
from django.contrib.auth.models import User as DjangoUser
from datetime import timedelta
from .models import User, OnCallSchedule, Incident, EscalationLevel
from .services import IncidentService, OnCallService, MetricsService


class OnCallServiceTests(TestCase):
    """Test on-call schedule lookup logic"""
    
    def setUp(self):
        """Create test users and schedules"""
        self.alice = DjangoUser.objects.create_user(
            username='alice',
            email='alice@example.com',
            password='testpass123'
        )
        self.bob = DjangoUser.objects.create_user(
            username='bob',
            email='bob@example.com',
            password='testpass123'
        )
        self.manager = DjangoUser.objects.create_user(
            username='manager',
            email='manager@example.com',
            password='testpass123'
        )
        
        self.now = timezone.now()
    
    def test_get_on_call_user_exists(self):
        """Test getting on-call user when schedule exists"""
        start = self.now - timedelta(hours=1)
        end = self.now + timedelta(hours=1)
        
        OnCallSchedule.objects.create(
            user=self.alice,
            service_name='payments',
            start_time=start,
            end_time=end,
            is_override=False
        )
        
        user = OnCallService.get_on_call_user('payments', self.now)
        self.assertEqual(user, self.alice)
    
    def test_get_on_call_user_not_found(self):
        """Test when no on-call user is available"""
        user = OnCallService.get_on_call_user('non_existent_service', self.now)
        self.assertIsNone(user)
    
    def test_get_on_call_user_outside_schedule(self):
        """Test when current time is outside schedule window"""
        start = self.now + timedelta(hours=1)
        end = self.now + timedelta(hours=2)
        
        OnCallSchedule.objects.create(
            user=self.alice,
            service_name='payments',
            start_time=start,
            end_time=end
        )
        
        user = OnCallService.get_on_call_user('payments', self.now)
        self.assertIsNone(user)
    
    def test_override_priority(self):
        """Test that override schedules take priority"""
        start = self.now - timedelta(hours=1)
        end = self.now + timedelta(hours=1)
        
        # Regular schedule
        OnCallSchedule.objects.create(
            user=self.alice,
            service_name='payments',
            start_time=start,
            end_time=end,
            is_override=False
        )
        
        # Override schedule
        OnCallSchedule.objects.create(
            user=self.bob,
            service_name='payments',
            start_time=start,
            end_time=end,
            is_override=True
        )
        
        user = OnCallService.get_on_call_user('payments', self.now)
        self.assertEqual(user, self.bob)


class IncidentServiceTests(TestCase):
    """Test incident creation, state transitions, and escalation"""
    
    def setUp(self):
        """Create test data"""
        self.alice = DjangoUser.objects.create_user(
            username='alice',
            email='alice@example.com'
        )
        self.bob = DjangoUser.objects.create_user(
            username='bob',
            email='bob@example.com'
        )
        self.manager = DjangoUser.objects.create_user(
            username='manager',
            email='manager@example.com'
        )
        
        self.now = timezone.now()
        
        # Create schedule for alice
        OnCallSchedule.objects.create(
            user=self.alice,
            service_name='payments',
            start_time=self.now - timedelta(hours=1),
            end_time=self.now + timedelta(hours=1)
        )
        
        # Create escalation levels
        EscalationLevel.objects.create(
            service_name='payments',
            level=1
        )
        EscalationLevel.objects.create(
            service_name='payments',
            level=2
        )
    
    def test_create_incident_auto_assigns(self):
        """Test incident is auto-assigned to on-call user"""
        incident = IncidentService.create_incident(
            title='DB Connection Failed',
            description='Cannot connect to database',
            service_name='payments',
            auto_assign=True,
            deduplication_enabled=False
        )
        
        self.assertEqual(incident.status, Incident.STATUS_TRIGGERED)
        self.assertEqual(incident.assigned_to, self.alice)
        self.assertIsNotNone(incident.created_at)
    
    def test_create_incident_no_oncall_user(self):
        """Test incident creation when no on-call user is available"""
        incident = IncidentService.create_incident(
            title='Test Incident',
            description='Test',
            service_name='non_existent_service',
            auto_assign=True,
            deduplication_enabled=False
        )
        
        self.assertEqual(incident.status, Incident.STATUS_TRIGGERED)
        self.assertIsNone(incident.assigned_to)
    
    def test_deduplication_works(self):
        """Test duplicate incidents are detected"""
        # Create first incident
        incident1 = IncidentService.create_incident(
            title='DB Connection Failed',
            description='First occurrence',
            service_name='payments',
            auto_assign=True,
            deduplication_enabled=True
        )
        
        # Create duplicate incident
        incident2 = IncidentService.create_incident(
            title='DB Connection Failed',
            description='Second occurrence',
            service_name='payments',
            auto_assign=True,
            deduplication_enabled=True
        )
        
        # Should return the same incident
        self.assertEqual(incident1.id, incident2.id)
    
    def test_acknowledge_incident(self):
        """Test acknowledging an incident"""
        incident = IncidentService.create_incident(
            title='Test',
            description='Test',
            service_name='payments',
            auto_assign=True,
            deduplication_enabled=False
        )
        
        acknowledged = IncidentService.acknowledge_incident(incident.id)
        
        self.assertEqual(acknowledged.status, Incident.STATUS_ACKNOWLEDGED)
        self.assertIsNotNone(acknowledged.acknowledged_at)
    
    def test_cannot_acknowledge_twice(self):
        """Test that acknowledged incident cannot be acknowledged again"""
        incident = IncidentService.create_incident(
            title='Test',
            description='Test',
            service_name='payments',
            auto_assign=True,
            deduplication_enabled=False
        )
        
        IncidentService.acknowledge_incident(incident.id)
        
        with self.assertRaises(ValueError):
            IncidentService.acknowledge_incident(incident.id)
    
    def test_resolve_incident(self):
        """Test resolving an acknowledged incident"""
        incident = IncidentService.create_incident(
            title='Test',
            description='Test',
            service_name='payments',
            auto_assign=True,
            deduplication_enabled=False
        )
        
        IncidentService.acknowledge_incident(incident.id)
        resolved = IncidentService.resolve_incident(incident.id)
        
        self.assertEqual(resolved.status, Incident.STATUS_RESOLVED)
        self.assertIsNotNone(resolved.resolved_at)
    
    def test_cannot_resolve_triggered_incident(self):
        """Test that triggered incident cannot be resolved directly"""
        incident = IncidentService.create_incident(
            title='Test',
            description='Test',
            service_name='payments',
            auto_assign=True,
            deduplication_enabled=False
        )
        
        with self.assertRaises(ValueError):
            IncidentService.resolve_incident(incident.id)
    
    def test_escalate_incident(self):
        """Test escalating an incident"""
        incident = IncidentService.create_incident(
            title='Test',
            description='Test',
            service_name='payments',
            auto_assign=True,
            deduplication_enabled=False
        )
        
        escalated = IncidentService.escalate_incident(incident.id)
        
        self.assertEqual(escalated.status, Incident.STATUS_ESCALATED)
        self.assertIsNotNone(escalated.escalated_at)
        # User remains the same (escalation is now user-independent)
        self.assertEqual(escalated.assigned_to, self.alice)
    
    def test_cannot_escalate_acknowledged_incident(self):
        """Test that acknowledged incident cannot be escalated"""
        incident = IncidentService.create_incident(
            title='Test',
            description='Test',
            service_name='payments',
            auto_assign=True,
            deduplication_enabled=False
        )
        
        IncidentService.acknowledge_incident(incident.id)
        
        with self.assertRaises(ValueError):
            IncidentService.escalate_incident(incident.id)
    
    def test_check_escalations(self):
        """Test automatic escalation of timed-out incidents"""
        # Create incident with old created_at (bypassing auto_now_add)
        old_time = timezone.now() - timedelta(minutes=10)  # 10 minutes old
        
        # First create the incident normally
        incident = Incident.objects.create(
            title='Old Incident',
            description='Created a while ago',
            service_name='payments',
            status=Incident.STATUS_TRIGGERED,
            assigned_to=self.alice
        )
        
        # Then update the created_at to an older time
        Incident.objects.filter(id=incident.id).update(created_at=old_time)
        
        # Run escalation check with short timeout (5 minutes)
        escalated_count = IncidentService.check_escalations(timeout_seconds=5 * 60)
        
        # Should escalate at least 1 incident
        self.assertGreaterEqual(escalated_count, 1)
        
        # Reload incident and verify status
        incident.refresh_from_db()
        self.assertEqual(incident.status, Incident.STATUS_ESCALATED)
        # User remains assigned (escalation is now user-independent)
        self.assertEqual(incident.assigned_to, self.alice)


class IncidentStateTransitionTests(TestCase):
    """Test strict state transition rules"""
    
    def setUp(self):
        self.alice = DjangoUser.objects.create_user(
            username='alice',
            email='alice@example.com'
        )
        self.now = timezone.now()
    
    def test_invalid_transitions(self):
        """Test that invalid state transitions are rejected"""
        incident = Incident.objects.create(
            title='Test',
            description='Test',
            service_name='payments',
            status=Incident.STATUS_ACKNOWLEDGED,
            assigned_to=self.alice,
            acknowledged_at=self.now
        )
        
        # Cannot escalate an acknowledged incident
        with self.assertRaises(ValueError):
            IncidentService.escalate_incident(incident.id)
        
        # Cannot acknowledge a resolved incident
        IncidentService.resolve_incident(incident.id)
        with self.assertRaises(ValueError):
            IncidentService.acknowledge_incident(incident.id)


class MetricsServiceTests(TestCase):
    """Test metrics calculation"""
    
    def setUp(self):
        self.alice = DjangoUser.objects.create_user(
            username='alice',
            email='alice@example.com'
        )
        self.now = timezone.now()
    
    def test_calculate_mtta(self):
        """Test MTTA calculation"""
        incident = Incident.objects.create(
            title='Test',
            description='Test',
            service_name='payments',
            status=Incident.STATUS_ACKNOWLEDGED,
            assigned_to=self.alice,
            created_at=self.now,
            acknowledged_at=self.now + timedelta(minutes=5)
        )
        
        mtta = MetricsService.calculate_mtta(incident)
        self.assertAlmostEqual(mtta, 5.0, places=0)  # 5 minutes (allow small timing variations)
    
    def test_calculate_mttr(self):
        """Test MTTR calculation"""
        incident = Incident.objects.create(
            title='Test',
            description='Test',
            service_name='payments',
            status=Incident.STATUS_RESOLVED,
            assigned_to=self.alice,
            created_at=self.now,
            resolved_at=self.now + timedelta(minutes=30)
        )
        
        mttr = MetricsService.calculate_mttr(incident)
        self.assertAlmostEqual(mttr, 30.0, places=0)  # 30 minutes (allow small timing variations)
    
    def test_get_metrics(self):
        """Test aggregate metrics calculation"""
        # Create resolved incident
        Incident.objects.create(
            title='Incident 1',
            description='Test',
            service_name='payments',
            status=Incident.STATUS_RESOLVED,
            assigned_to=self.alice,
            created_at=self.now,
            acknowledged_at=self.now + timedelta(minutes=5),
            resolved_at=self.now + timedelta(minutes=20)
        )
        
        # Create another resolved incident
        Incident.objects.create(
            title='Incident 2',
            description='Test',
            service_name='payments',
            status=Incident.STATUS_RESOLVED,
            assigned_to=self.alice,
            created_at=self.now,
            acknowledged_at=self.now + timedelta(minutes=3),
            resolved_at=self.now + timedelta(minutes=25)
        )
        
        metrics = MetricsService.get_metrics(service_name='payments')
        
        self.assertEqual(metrics['total_incidents'], 2)
        self.assertEqual(metrics['resolved_count'], 2)
        self.assertAlmostEqual(metrics['mtta_minutes'], 4.0, places=0)  # Average of 5 and 3
        self.assertAlmostEqual(metrics['mttr_minutes'], 22.5, places=0)  # Average of 20 and 25
    
    def test_get_metrics_empty(self):
        """Test metrics when no incidents exist"""
        metrics = MetricsService.get_metrics(service_name='non_existent')
        
        self.assertEqual(metrics['total_incidents'], 0)
        self.assertEqual(metrics['resolved_count'], 0)
        self.assertIsNone(metrics['mtta_minutes'])
        self.assertIsNone(metrics['mttr_minutes'])

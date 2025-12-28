from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User as DjangoUser
from django.conf import settings
import random
import hashlib


class User(models.Model):
    """
    Custom user model for on-call incident management.
    Used alongside Django's auth user for flexibility.
    """
    first_name = models.CharField(max_length=30)  
    last_name = models.CharField(max_length=30)   
    email = models.EmailField()
    address = models.CharField(max_length=255)
    country = models.CharField(max_length=100)
    state = models.CharField(max_length=100)      
    city = models.CharField(max_length=100)
    pincode = models.CharField(max_length=10)
    mobile_number = models.CharField(max_length=20)  
    password = models.CharField(max_length=128)     

    def __str__(self):
        return f"{self.first_name} {self.last_name}"


class OnCallSchedule(models.Model):
    """
    Model to manage on-call schedules.
    Each record defines who is on-call for a service during a time period.
    """
    user = models.ForeignKey(DjangoUser, on_delete=models.CASCADE, related_name='oncall_schedules')
    service_name = models.CharField(max_length=100)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    is_override = models.BooleanField(default=False, help_text="Override takes priority over regular schedule")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-is_override', 'start_time']
        indexes = [
            models.Index(fields=['service_name', 'start_time', 'end_time']),
        ]
    
    def __str__(self):
        return f"{self.service_name} - {self.user.username} ({self.start_time} to {self.end_time})"
    
    def is_active_at(self, current_time):
        """Check if this schedule is active at given time"""
        return self.start_time <= current_time <= self.end_time


class Incident(models.Model):
    """
    Model to represent incidents in the on-call system.
    Manages lifecycle: TRIGGERED -> ACKNOWLEDGED -> RESOLVED (or ESCALATED)
    """
    # Incident status constants
    STATUS_TRIGGERED = 'TRIGGERED'
    STATUS_ACKNOWLEDGED = 'ACKNOWLEDGED'
    STATUS_RESOLVED = 'RESOLVED'
    STATUS_ESCALATED = 'ESCALATED'
    
    STATUS_CHOICES = [
        (STATUS_TRIGGERED, 'Triggered'),
        (STATUS_ACKNOWLEDGED, 'Acknowledged'),
        (STATUS_RESOLVED, 'Resolved'),
        (STATUS_ESCALATED, 'Escalated'),
    ]
    
    # Core fields
    title = models.CharField(max_length=255)
    description = models.TextField()
    service_name = models.CharField(max_length=100)
    
    # Status and assignment
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_TRIGGERED
    )
    assigned_to = models.ForeignKey(
        DjangoUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_incidents'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    escalated_at = models.DateTimeField(null=True, blank=True)
    
    # Deduplication
    deduplication_key = models.CharField(
        max_length=64,
        null=True,
        blank=True,
        db_index=True,
        help_text="Hash of service_name + title for deduplication"
    )
    
    # Legacy fields (kept for backward compatibility)
    incident_id = models.CharField(max_length=20, unique=True, null=True, blank=True)
    reporter_id = models.CharField(max_length=20, null=True, blank=True)
    reporter = models.CharField(max_length=40, null=True, blank=True)
    priority = models.CharField(
        max_length=10,
        choices=[('High', 'High'), ('Medium', 'Medium'), ('Low', 'Low')],
        default='Medium'
    )
    is_enterprise = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['service_name', 'status']),
            models.Index(fields=['assigned_to', 'status']),
            models.Index(fields=['deduplication_key', 'created_at']),
        ]
    
    def generate_unique_incident_id(self):
        """Generate legacy incident ID format"""
        current_year = timezone.now().year
        random_number = random.randint(10000, 99999)
        return f'RMG{random_number}{current_year}'
    
    def save(self, *args, **kwargs):
        # Generate incident_id if not exists (for backward compatibility)
        if not self.incident_id:
            self.incident_id = self.generate_unique_incident_id()
        
        # Generate deduplication key if not provided
        if not self.deduplication_key:
            key_string = f"{self.service_name}:{self.title}"
            self.deduplication_key = hashlib.md5(key_string.encode()).hexdigest()
        
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.incident_id or 'N/A'} - {self.title} ({self.status})"
    
    @property
    def is_resolvable(self):
        """Check if incident can be resolved (must be acknowledged)"""
        return self.status == self.STATUS_ACKNOWLEDGED
    
    @property
    def is_acknowledgeable(self):
        """Check if incident can be acknowledged"""
        return self.status == self.STATUS_TRIGGERED
    
    @property
    def can_escalate(self):
        """Check if incident can be escalated"""
        return self.status == self.STATUS_TRIGGERED


class EscalationLevel(models.Model):
    """
    Model for managing escalation paths.
    Defines escalation tiers that will be notified when incident is escalated.
    """
    service_name = models.CharField(max_length=100)
    level = models.PositiveIntegerField(help_text="1=Primary, 2=Secondary, 3=Manager, etc")
    notification_channel = models.CharField(
        max_length=100,
        help_text="Email, Slack channel, PagerDuty ID, etc",
        default="admin"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = [['service_name', 'level']]
        ordering = ['service_name', 'level']
    
    def __str__(self):
        return f"{self.service_name} - Level {self.level}: {self.notification_channel}"
    
    
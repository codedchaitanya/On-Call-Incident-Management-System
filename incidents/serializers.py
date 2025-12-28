# incidents/serializers.py
from rest_framework import serializers
from .models import User, Incident, OnCallSchedule, EscalationLevel
from django.contrib.auth.models import User as DjangoUser
from .services import IncidentService


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = '__all__'


class DjangoUserSerializer(serializers.ModelSerializer):
    """Serializer for Django's built-in User model"""
    class Meta:
        model = DjangoUser
        fields = ['id', 'username', 'email', 'first_name', 'last_name']
        read_only_fields = ['id']


class OnCallScheduleSerializer(serializers.ModelSerializer):
    user = DjangoUserSerializer(read_only=True)
    user_id = serializers.IntegerField(write_only=True)
    
    class Meta:
        model = OnCallSchedule
        fields = ['id', 'user', 'user_id', 'service_name', 'start_time', 'end_time', 'is_override', 'created_at']
        read_only_fields = ['id', 'created_at']
    
    def create(self, validated_data):
        user_id = validated_data.pop('user_id')
        user = DjangoUser.objects.get(id=user_id)
        return OnCallSchedule.objects.create(user=user, **validated_data)


class IncidentSerializer(serializers.ModelSerializer):
    """Serializer for creating incidents (trigger endpoint)"""
    assigned_to = DjangoUserSerializer(read_only=True)
    
    class Meta:
        model = Incident
        fields = ['id', 'title', 'description', 'service_name', 'status', 'assigned_to', 
                 'created_at', 'acknowledged_at', 'resolved_at', 'escalated_at']
        read_only_fields = ['id', 'status', 'assigned_to', 'created_at', 'acknowledged_at', 
                           'resolved_at', 'escalated_at']


class IncidentDetailSerializer(serializers.ModelSerializer):
    """Detailed serializer with all incident info"""
    assigned_to = DjangoUserSerializer(read_only=True)
    
    class Meta:
        model = Incident
        fields = ['id', 'title', 'description', 'service_name', 'status', 'assigned_to',
                 'created_at', 'acknowledged_at', 'resolved_at', 'escalated_at', 
                 'deduplication_key', 'incident_id', 'priority', 'is_enterprise']
        read_only_fields = ['id', 'created_at', 'acknowledged_at', 'resolved_at', 'escalated_at',
                           'deduplication_key', 'incident_id']


class IncidentStateTransitionSerializer(serializers.Serializer):
    """Serializer for incident state transitions (acknowledge, resolve, escalate)"""
    detail = serializers.CharField(read_only=True)
    incident = IncidentDetailSerializer(read_only=True)
    
    def validate(self, data):
        # State transition validation will be done in views
        return data


class EscalationLevelSerializer(serializers.ModelSerializer):
    class Meta:
        model = EscalationLevel
        fields = ['id', 'service_name', 'level', 'notification_channel', 'created_at']
        read_only_fields = ['id', 'created_at']



class GetIncidentSerializer(serializers.ModelSerializer):
    """Legacy serializer for backward compatibility"""
    class Meta:
        model = Incident
        fields = '__all__'

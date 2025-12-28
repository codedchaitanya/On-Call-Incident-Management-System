from rest_framework import generics, status, viewsets
from rest_framework.response import Response
from rest_framework.decorators import action
from .models import User, Incident, OnCallSchedule, EscalationLevel
from django.contrib.auth.models import User as DjangoUser
from .serializers import (
    UserSerializer, IncidentSerializer, GetIncidentSerializer,
    DjangoUserSerializer, OnCallScheduleSerializer, IncidentDetailSerializer,
    EscalationLevelSerializer
)
import requests
import json
from django.shortcuts import get_object_or_404
from django.http import Http404
from rest_framework.exceptions import ValidationError
from django.contrib.auth.hashers import make_password
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import BasicAuthentication
from .services import IncidentService, OnCallService, MetricsService
from .notifications import NotificationService
from django.utils import timezone


# ===== EXISTING LEGACY ENDPOINTS (for backward compatibility) =====

class GetInfofromPin(generics.ListAPIView):
    def get(self, request, *args, **kwargs):
        pincode = self.kwargs['pincode']
        endpoint = f'https://api.postalpincode.in/pincode/{pincode}'
        response = requests.get(endpoint)

        if response.status_code == 200:
            pincode_information = json.loads(response.text)
            if pincode_information and isinstance(pincode_information, list):
                city = pincode_information[0].get('PostOffice', [])[0].get('District', '')
                state = pincode_information[0].get('PostOffice', [])[0].get('State', '')
                country = pincode_information[0].get('PostOffice', [])[0].get('Country', '')
                return Response({'city': city,'state':state, 'country': country}, status=status.HTTP_200_OK)
        return Response({'detail': 'Pincode not found'}, status=status.HTTP_404_NOT_FOUND)


class UserCreateView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer

    def post(self, request, *args, **kwargs):
        # Extract the pin code from the request data
        pincode = request.data.get('pincode')

        # Make an AJAX request to GetInfofromPin view to fetch city and country information
        response = requests.get(f'http://127.0.0.1:8000/api/pincode/{pincode}/')

        if response.status_code == 200:
            data = response.json()
            # Update the request data with the fetched City and Country
            request.data['city'] = data.get('city', '')
            request.data['state'] = data.get('state', '')
            request.data['country'] = data.get('country', '')
            
            # Check if a user with the same username (first_name+last_name) already exists
            username = request.data['first_name'] +" "+ request.data['last_name']
            try:
                existing_user = DjangoUser.objects.get(username=username)
                return Response({'detail': 'Username already registered'}, status=status.HTTP_400_BAD_REQUEST)
            except DjangoUser.DoesNotExist:
                pass  # The user does not exist, continue with user creation

            # Create the user in the custom incidents_user table
            user_serializer = self.get_serializer(data=request.data)
            user_serializer.is_valid(raise_exception=True)
            # Hash the password using Django's make_password function
            hashed_password = make_password(request.data['password'])
            user_serializer.validated_data['password'] = hashed_password
            user_serializer.save()
            # Create the user in the auth_user table
            auth_user = DjangoUser(
                username=username,  # Set the username as first_name+last_name
                email=request.data['email'],
                password=hashed_password,  # Make sure to hash the password
            )
            auth_user.save()
            return Response({'detail': 'User created successfully'}, status=status.HTTP_201_CREATED)
        else:
            return Response({'detail': 'Failed to fetch pincode information'}, status=response.status_code)


class UserListView(generics.ListAPIView):
    serializer_class = UserSerializer

    def get_queryset(self):
        user_id = self.request.query_params.get('user_id')

        if user_id:
            try:
                user = User.objects.get(id=user_id)
                return [user]  # Return a list containing the single user
            except User.DoesNotExist:
                raise Http404("User does not exist")

        # If user_id is not provided, return all users
        return User.objects.all()

    def get(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.serializer_class(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class UserUpdateView(generics.UpdateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer

    def update(self, request, *args, **kwargs):
        # Extract user_id from the request data
        user_id = request.query_params.get('user_id')

        if user_id is None:
            # If user_id is not provided, return a validation error response
            raise ValidationError({'user_id': ['User ID must be provided for update.']})

        # Get the user object based on user_id
        instance = get_object_or_404(User, pk=user_id)

        serializer = self.get_serializer(instance, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({'detail': 'User updated successfully'}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class UserDeleteView(generics.DestroyAPIView):
    queryset = User.objects.all()

    def destroy(self, request, *args, **kwargs):
        user_id = request.query_params.get('user_id')

        if user_id is None:
            # If user_id is not provided, return a validation error response
            return Response({'detail': 'User ID must be provided for deletion.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            instance = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            # If the user with the provided user_id does not exist, return a not found response
            return Response({'detail': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

        # Perform the deletion
        instance.delete()

        return Response({'detail': 'User deleted successfully'}, status=status.HTTP_204_NO_CONTENT)

class IncidentCreateView(generics.CreateAPIView):
    queryset = Incident.objects.all()
    serializer_class = IncidentSerializer

    def create(self, request, *args, **kwargs):
        # Check if the reporter exists based on their user ID (assuming it's provided in the request)
        reporter_id = request.data.get('reporter_id')
        try:
            reporter_name = User.objects.get(pk=reporter_id)
        except User.DoesNotExist:
            # Log a message if the reporter does not exist
            return Response({'detail': 'Reporter not found'}, status=status.HTTP_404_NOT_FOUND)

          # Add reporter_name to the request data as 'reporter'
        request.data['reporter'] = str(reporter_name)

         # Use the modified request data to create the incident
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            # Create the incident record (without saving it to the database)
            incident = serializer.save()
            return Response({'detail': 'Incident created successfully'}, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class IncidentListView(generics.ListAPIView):
    serializer_class = GetIncidentSerializer
    authentication_classes = [BasicAuthentication]  # Use Basic Authentication
    permission_classes = [IsAuthenticated]  # Require authentication

    def get_queryset(self):
        queryset = Incident.objects.filter(reporter=self.request.user)  # Filter by the authenticated user
        return queryset

    def list(self, request, *args, **kwargs):
        try:
            queryset = self.get_queryset()
            serializer = self.get_serializer(queryset, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            
            return Response({'detail': 'An error occurred'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class IncidentSearchView(generics.ListAPIView):
    serializer_class = GetIncidentSerializer

    def get_queryset(self):
        incident_id = self.request.query_params.get('incident_id')
        if incident_id:
            queryset = Incident.objects.filter(incident_id=incident_id)
        else:
            queryset = Incident.objects.none()
        return queryset

    def list(self, request, *args, **kwargs):
        incident_id = self.request.query_params.get('incident_id')
        if not incident_id:
            return Response({'detail': 'The "incident_id" parameter is required for searching.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            queryset = self.get_queryset()
            serializer = self.get_serializer(queryset, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            
            return Response({'detail': 'An error occurred'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class IncidentUpdateView(generics.UpdateAPIView):
    serializer_class = IncidentSerializer
    permission_classes = [IsAuthenticated]  # Require authentication

    def get_object(self):
        incident_id = self.request.query_params.get('incident_id')
        if incident_id is None:
            # If incident_id is not provided, return a validation error response
            raise ValidationError({'incident_id': ['Incident ID must be provided for update.']})

        try:
            # Check if the incident belongs to the authenticated user
            return Incident.objects.get(incident_id=incident_id, reporter=self.request.user)
        except Incident.DoesNotExist:
            return None

    def update(self, request, *args, **kwargs):
        instance = self.get_object()

        if instance is None:
            return Response({'detail': 'Incident not found or you do not have permission to edit it.'}, status=status.HTTP_404_NOT_FOUND)
        
        # Check if the incident is closed before allowing the update
        if instance.status == 'Closed':
            return Response({'detail': 'Closed incidents cannot be edited.'}, status=status.HTTP_400_BAD_REQUEST)
        
        serializer = self.get_serializer(instance, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({'detail': 'Incident updated successfully'}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    

class IncidentDeleteView(generics.DestroyAPIView):
    serializer_class = IncidentSerializer

    def get_object(self):
        incident_id = self.request.query_params.get('incident_id')
        try:
            return Incident.objects.get(incident_id=incident_id)
        except Incident.DoesNotExist:
            return None

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()

        if instance is None:
            return Response({'detail': 'Incident not found'}, status=status.HTTP_404_NOT_FOUND)

        instance.delete()
        return Response({'detail': 'Incident deleted successfully'}, status=status.HTTP_204_NO_CONTENT)


# ===== NEW ON-CALL INCIDENT MANAGEMENT ENDPOINTS =====

class IncidentTriggerView(generics.CreateAPIView):
    """
    Trigger a new incident via API.
    
    POST /api/incidents/trigger/
    {
        "service_name": "payments",
        "title": "DB connection failed",
        "description": "Timeout while connecting to DB"
    }
    """
    queryset = Incident.objects.all()
    serializer_class = IncidentSerializer
    
    def create(self, request, *args, **kwargs):
        title = request.data.get('title')
        description = request.data.get('description')
        service_name = request.data.get('service_name')
        
        if not all([title, service_name]):
            error_msg = 'title and service_name are required'
            NotificationService.error('❌ Missing Fields', error_msg)
            return Response(
                {'detail': error_msg},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            incident = IncidentService.create_incident(
                title=title,
                description=description or '',
                service_name=service_name,
                auto_assign=True,
                deduplication_enabled=True
            )
            
            serializer = self.get_serializer(incident)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            error_msg = str(e)
            NotificationService.error('❌ Error', f'Failed to trigger incident: {error_msg}')
            return Response(
                {'detail': error_msg},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class IncidentAcknowledgeView(generics.UpdateAPIView):
    """
    Acknowledge an incident.
    
    POST /api/incidents/{id}/acknowledge/
    """
    queryset = Incident.objects.all()
    serializer_class = IncidentDetailSerializer
    lookup_field = 'id'
    
    def update(self, request, *args, **kwargs):
        incident_id = kwargs.get('id')
        
        try:
            incident = IncidentService.acknowledge_incident(incident_id)
            serializer = self.get_serializer(incident)
            return Response(
                {'detail': 'Incident acknowledged', 'incident': serializer.data},
                status=status.HTTP_200_OK
            )
        except ValueError as e:
            error_msg = str(e)
            NotificationService.error('❌ Error', f'Failed to acknowledge incident: {error_msg}')
            return Response(
                {'detail': error_msg},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            error_msg = str(e)
            NotificationService.error('❌ Error', f'An error occurred: {error_msg}')
            return Response(
                {'detail': error_msg},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class IncidentResolveView(generics.UpdateAPIView):
    """
    Resolve an incident.
    
    POST /api/incidents/{id}/resolve/
    """
    queryset = Incident.objects.all()
    serializer_class = IncidentDetailSerializer
    lookup_field = 'id'
    
    def update(self, request, *args, **kwargs):
        incident_id = kwargs.get('id')
        
        try:
            incident = IncidentService.resolve_incident(incident_id)
            serializer = self.get_serializer(incident)
            return Response(
                {'detail': 'Incident resolved', 'incident': serializer.data},
                status=status.HTTP_200_OK
            )
        except ValueError as e:
            error_msg = str(e)
            NotificationService.error('❌ Error', f'Failed to resolve incident: {error_msg}')
            return Response(
                {'detail': error_msg},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            error_msg = str(e)
            NotificationService.error('❌ Error', f'An error occurred: {error_msg}')
            return Response(
                {'detail': error_msg},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class IncidentEscalateView(generics.UpdateAPIView):
    """
    Manually escalate an incident.
    
    POST /api/incidents/{id}/escalate/
    """
    queryset = Incident.objects.all()
    serializer_class = IncidentDetailSerializer
    lookup_field = 'id'
    
    def update(self, request, *args, **kwargs):
        incident_id = kwargs.get('id')
        
        try:
            incident = IncidentService.escalate_incident(incident_id)
            serializer = self.get_serializer(incident)
            return Response(
                {'detail': 'Incident escalated', 'incident': serializer.data},
                status=status.HTTP_200_OK
            )
        except ValueError as e:
            error_msg = str(e)
            NotificationService.error('❌ Error', f'Failed to escalate incident: {error_msg}')
            return Response(
                {'detail': error_msg},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            error_msg = str(e)
            NotificationService.error('❌ Error', f'An error occurred: {error_msg}')
            return Response(
                {'detail': error_msg},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class EscalationCheckView(generics.GenericAPIView):
    """
    Check and escalate incidents that have exceeded timeout.
    
    POST /api/incidents/escalate/check/
    """
    
    def post(self, request, *args, **kwargs):
        try:
            escalated_count = IncidentService.check_escalations()
            return Response(
                {
                    'detail': f'Escalation check completed',
                    'escalated_count': escalated_count
                },
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                {'detail': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class OnCallScheduleViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing on-call schedules.
    
    GET /api/oncall/schedules/ - List all schedules
    POST /api/oncall/schedules/ - Create schedule
    GET /api/oncall/schedules/{id}/ - Get schedule
    PUT /api/oncall/schedules/{id}/ - Update schedule
    DELETE /api/oncall/schedules/{id}/ - Delete schedule
    """
    queryset = OnCallSchedule.objects.all()
    serializer_class = OnCallScheduleSerializer
    
    @action(detail=False, methods=['get'])
    def current(self, request):
        """Get current on-call user for a service"""
        service_name = request.query_params.get('service_name')
        
        if not service_name:
            return Response(
                {'detail': 'service_name is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user = OnCallService.get_on_call_user(service_name)
        if user:
            serializer = DjangoUserSerializer(user)
            return Response(
                {'on_call_user': serializer.data},
                status=status.HTTP_200_OK
            )
        else:
            return Response(
                {'detail': f'No on-call user for {service_name}'},
                status=status.HTTP_404_NOT_FOUND
            )


class EscalationLevelViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing escalation levels.
    
    Defines the escalation path for each service.
    Example: Service "payments" -> Level 1: Alice -> Level 2: Bob -> Level 3: Manager
    """
    queryset = EscalationLevel.objects.all()
    serializer_class = EscalationLevelSerializer


class MetricsView(generics.GenericAPIView):
    """
    Get incident metrics.
    
    GET /api/metrics/?service_name=payments&start_date=2025-01-01&end_date=2025-01-31
    
    Returns:
    {
        "mtta_minutes": 2.5,
        "mttr_minutes": 15.3,
        "total_incidents": 10,
        "resolved_count": 10,
        "avg_response_time": 2.5
    }
    """
    
    def get(self, request, *args, **kwargs):
        service_name = request.query_params.get('service_name')
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        
        try:
            metrics = MetricsService.get_metrics(
                service_name=service_name,
                start_date=start_date,
                end_date=end_date
            )
            return Response(metrics, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {'detail': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class IncidentListDetailView(generics.ListAPIView):
    """
    Get all incidents with detailed info.
    
    GET /api/incidents/list/all/
    """
    queryset = Incident.objects.all()
    serializer_class = IncidentDetailSerializer
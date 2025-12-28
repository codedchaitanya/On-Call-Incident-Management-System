"""
Management command to check and escalate incidents that have exceeded timeout.

Usage:
    python manage.py check_incident_escalations
    python manage.py check_incident_escalations --timeout 300  # custom timeout in seconds
"""

from django.core.management.base import BaseCommand
from incidents.services import IncidentService


class Command(BaseCommand):
    help = 'Check and escalate incidents that have exceeded timeout'

    def add_arguments(self, parser):
        parser.add_argument(
            '--timeout',
            type=int,
            default=None,
            help='Escalation timeout in seconds (default: 5 minutes)',
        )

    def handle(self, *args, **options):
        timeout = options.get('timeout')
        
        self.stdout.write(self.style.SUCCESS('Starting escalation check...'))
        
        try:
            escalated_count = IncidentService.check_escalations(timeout_seconds=timeout)
            
            if escalated_count > 0:
                self.stdout.write(
                    self.style.SUCCESS(f'✓ Successfully escalated {escalated_count} incident(s)')
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS('✓ No incidents to escalate')
                )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'✗ Escalation check failed: {str(e)}')
            )

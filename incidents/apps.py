from django.apps import AppConfig
import logging

logger = logging.getLogger(__name__)


class IncidentsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'incidents'
    
    def ready(self):
        """Initialize background scheduler when app is ready"""
        try:
            from .scheduler import start_scheduler
            start_scheduler()
            logger.info("Incidents app initialized with background scheduler")
        except Exception as e:
            logger.error(f"Failed to initialize scheduler: {e}")

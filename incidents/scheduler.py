"""
Background scheduler for automated escalation checks.
Runs escalation check every minute using a simple thread-based approach.
Uses memory jobstore to avoid SQLite locking issues.
"""

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.jobstores.memory import MemoryJobStore
import logging
import pytz

logger = logging.getLogger(__name__)


def check_escalations_job():
    """Background job to check and escalate incidents"""
    try:
        from .services import IncidentService
        
        escalated_count = IncidentService.check_escalations()
        if escalated_count > 0:
            logger.info(f"[SCHEDULER] Auto-escalated {escalated_count} incidents")
        
    except Exception as e:
        logger.error(f"[SCHEDULER] Error during escalation check: {e}")


def start_scheduler():
    """Start the background scheduler"""
    scheduler = BackgroundScheduler(timezone=pytz.UTC)
    
    # Use memory jobstore to avoid SQLite locking issues
    scheduler.add_jobstore(MemoryJobStore(), "default")
    
    # Run escalation check every 1 minute
    scheduler.add_job(
        check_escalations_job,
        trigger=IntervalTrigger(minutes=1),
        id='check_escalations',
        name='Check and escalate incidents',
        replace_existing=True,
    )
    
    scheduler.start()
    logger.info("[SCHEDULER] Background escalation scheduler started (Memory-based)")

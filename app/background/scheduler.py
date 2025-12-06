"""
Background Job Scheduler
Uses APScheduler to run background tasks
"""

import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime

from app.core.config import settings
from app.core.database import get_db_pool

logger = logging.getLogger(__name__)


class BackgroundScheduler:
    """
    Manages all background jobs using APScheduler
    """
    
    def __init__(self):
        self.scheduler = AsyncIOScheduler(timezone="Asia/Kolkata")
        self.jobs = {}
    
    # ========================================================================
    # SCHEDULER LIFECYCLE
    # ========================================================================
    
    async def start(self):
        """Start the scheduler and add all jobs"""
        logger.info("=" * 70)
        logger.info(" STARTING BACKGROUND SCHEDULER")
        logger.info("=" * 70)
        
        try:
            # Import job functions
            from app.background.jobs.portfolio_price_update import update_all_portfolio_prices
            from app.background.jobs.portfolio_report_job import send_portfolio_reports
            from app.background.jobs.cleanup_jobs import cleanup_expired_otps, cleanup_revoked_tokens
            
            # Get database pool
            db_pool = await get_db_pool()
            
            # ================================================================
            # JOB 1: PORTFOLIO PRICE UPDATE (Every 30 minutes)
            # ================================================================
            self.scheduler.add_job(
                func=update_all_portfolio_prices,
                trigger=IntervalTrigger(minutes=30),
                id="portfolio_price_update",
                name="Update Portfolio Prices",
                args=[db_pool],
                replace_existing=True,
                max_instances=1
            )
            logger.info(" Job added: Portfolio Price Update (every 30 mins)")
            
            # ================================================================
            # JOB 2: PORTFOLIO REPORTS (Daily at configured time)
            # ================================================================
            # This will be dynamically scheduled based on system_status settings
            # We'll check settings and add appropriate trigger
            self.scheduler.add_job(
                func=send_portfolio_reports,
                trigger=CronTrigger(hour=9, minute=0),  # Default: 9:00 AM IST
                id="portfolio_reports",
                name="Send Portfolio Reports",
                args=[db_pool],
                replace_existing=True,
                max_instances=1
            )
            logger.info(" Job added: Portfolio Reports (daily at 9:00 AM IST)")
            
            # ================================================================
            # JOB 3: CLEANUP EXPIRED OTPs (Every hour)
            # ================================================================
            self.scheduler.add_job(
                func=cleanup_expired_otps,
                trigger=IntervalTrigger(hours=1),
                id="cleanup_otps",
                name="Cleanup Expired OTPs",
                args=[db_pool],
                replace_existing=True,
                max_instances=1
            )
            logger.info(" Job added: Cleanup Expired OTPs (every hour)")
            
            # ================================================================
            # JOB 4: CLEANUP REVOKED TOKENS (Every 6 hours)
            # ================================================================
            self.scheduler.add_job(
                func=cleanup_revoked_tokens,
                trigger=IntervalTrigger(hours=6),
                id="cleanup_tokens",
                name="Cleanup Revoked Tokens",
                args=[db_pool],
                replace_existing=True,
                max_instances=1
            )
            logger.info(" Job added: Cleanup Revoked Tokens (every 6 hours)")
            
            # Start scheduler
            self.scheduler.start()
            
            logger.info("=" * 70)
            logger.info(" BACKGROUND SCHEDULER STARTED")
            logger.info("=" * 70)
            
            # Log scheduled jobs
            self._log_scheduled_jobs()
            
        except Exception as e:
            logger.error(f" Failed to start background scheduler: {e}")
            raise
    
    async def shutdown(self):
        """Shutdown the scheduler"""
        logger.info(" Shutting down background scheduler...")
        
        try:
            if self.scheduler.running:
                self.scheduler.shutdown(wait=True)
                logger.info(" Background scheduler shut down successfully")
        except Exception as e:
            logger.error(f"Error shutting down scheduler: {e}")
    
    # ========================================================================
    # JOB MANAGEMENT
    # ========================================================================
    
    def pause_job(self, job_id: str):
        """Pause a specific job"""
        try:
            self.scheduler.pause_job(job_id)
            logger.info(f"⏸  Job paused: {job_id}")
        except Exception as e:
            logger.error(f"Error pausing job {job_id}: {e}")
    
    def resume_job(self, job_id: str):
        """Resume a paused job"""
        try:
            self.scheduler.resume_job(job_id)
            logger.info(f"▶  Job resumed: {job_id}")
        except Exception as e:
            logger.error(f"Error resuming job {job_id}: {e}")
    
    def remove_job(self, job_id: str):
        """Remove a job"""
        try:
            self.scheduler.remove_job(job_id)
            logger.info(f"  Job removed: {job_id}")
        except Exception as e:
            logger.error(f"Error removing job {job_id}: {e}")
    
    def get_job(self, job_id: str):
        """Get job details"""
        return self.scheduler.get_job(job_id)
    
    def get_all_jobs(self):
        """Get all scheduled jobs"""
        return self.scheduler.get_jobs()
    
    # ========================================================================
    # DYNAMIC JOB SCHEDULING
    # ========================================================================
    
    async def update_portfolio_report_schedule(self, frequency: str, send_time: str, day_weekly: int = None, day_monthly: int = None):
        """
        Update portfolio report schedule dynamically
        
        Args:
            frequency: 'disabled', 'daily', 'weekly', 'monthly'
            send_time: Time in HH:MM format (24-hour)
            day_weekly: Day of week (0=Monday, 6=Sunday)
            day_monthly: Day of month (1-31)
        """
        job_id = "portfolio_reports"
        
        # Remove existing job
        try:
            self.scheduler.remove_job(job_id)
        except:
            pass
        
        # If disabled, don't add new job
        if frequency == "disabled":
            logger.info("Portfolio reports disabled")
            return
        
        # Parse time
        hour, minute = map(int, send_time.split(":"))
        
        # Import job function
        from app.background.jobs.portfolio_report_job import send_portfolio_reports
        db_pool = await get_db_pool()
        
        # Add job based on frequency
        if frequency == "daily":
            trigger = CronTrigger(hour=hour, minute=minute)
            
        elif frequency == "weekly":
            trigger = CronTrigger(day_of_week=day_weekly or 0, hour=hour, minute=minute)
            
        elif frequency == "monthly":
            trigger = CronTrigger(day=day_monthly or 1, hour=hour, minute=minute)
        
        else:
            logger.error(f"Invalid frequency: {frequency}")
            return
        
        self.scheduler.add_job(
            func=send_portfolio_reports,
            trigger=trigger,
            id=job_id,
            name="Send Portfolio Reports",
            args=[db_pool],
            replace_existing=True,
            max_instances=1
        )
        
        logger.info(f" Portfolio report schedule updated: {frequency} at {send_time}")
    
    # ========================================================================
    # UTILITIES
    # ========================================================================
    
    def _log_scheduled_jobs(self):
        """Log all scheduled jobs"""
        jobs = self.scheduler.get_jobs()
        
        logger.info(" Scheduled Jobs:")
        for job in jobs:
            next_run = job.next_run_time
            logger.info(f"  - {job.name} (ID: {job.id})")
            logger.info(f"    Next run: {next_run}")
    
    def is_running(self) -> bool:
        """Check if scheduler is running"""
        return self.scheduler.running
    
    def get_statistics(self):
        """Get scheduler statistics"""
        jobs = self.scheduler.get_jobs()
        
        return {
            "running": self.scheduler.running,
            "total_jobs": len(jobs),
            "jobs": [
                {
                    "id": job.id,
                    "name": job.name,
                    "next_run": job.next_run_time.isoformat() if job.next_run_time else None
                }
                for job in jobs
            ]
        }


# ========================================================================
# GLOBAL INSTANCE
# ========================================================================

background_scheduler = BackgroundScheduler()

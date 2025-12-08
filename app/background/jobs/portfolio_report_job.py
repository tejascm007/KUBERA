"""
Portfolio Report Job
Sends scheduled portfolio reports to users (daily/weekly/monthly)
"""

import logging
from datetime import datetime
import asyncpg
from app.db.repositories.system_repository import SystemRepository
from app.db.repositories.user_repository import UserRepository
from app.db.repositories.email_repository import EmailRepository
from app.services.portfolio_service import PortfolioService
from app.services.email_service import EmailService

logger = logging.getLogger(__name__)


async def send_portfolio_reports(db_pool: asyncpg.Pool):
    """
    Send portfolio reports to all users who have enabled them
    
    This job runs based on admin-configured schedule:
    - Daily: Every day at specified time
    - Weekly: Specific day of week at specified time
    - Monthly: Specific day of month at specified time
    
    Args:
        db_pool: Database connection pool
    """
    start_time = datetime.now()
    
    try:
        logger.info("=" * 70)
        logger.info(" STARTING PORTFOLIO REPORT JOB")
        logger.info(f"Started at: {start_time.strftime('%Y-%m-%d %H:%M:%S IST')}")
        logger.info("=" * 70)
        
        # Check system status
        system_repo = SystemRepository(db_pool)
        system_status = await system_repo.get_system_status()
        
        frequency = system_status.get('portfolio_report_frequency')
        
        if frequency == 'disabled':
            logger.info("Portfolio reports are disabled. Skipping...")
            return
        
        logger.info(f"Report frequency: {frequency}")
        
        # Get all users with portfolio reports enabled
        email_repo = EmailRepository(db_pool)
        users_with_reports = await email_repo.get_users_with_preference('portfolio_reports', True)
        
        logger.info(f"Found {len(users_with_reports)} users with reports enabled")
        
        if not users_with_reports:
            logger.info("No users to send reports to")
            return
        
        # Initialize services
        portfolio_service = PortfolioService(db_pool)
        email_service = EmailService(db_pool)
        
        sent_count = 0
        failed_count = 0
        
        # Send reports to each user
        for user in users_with_reports:
            try:
                user_id = user['user_id']
                
                # Get portfolio data
                portfolio_data = await portfolio_service.get_user_portfolio(user_id)
                
                # Skip if no portfolio entries
                if not portfolio_data['portfolio']:
                    logger.info(f"Skipping user {user_id}: No portfolio entries")
                    continue
                
                # Send report email
                success = await email_service.send_portfolio_report_email(user, portfolio_data)
                
                if success:
                    sent_count += 1
                    logger.info(f" Report sent to {user['email']}")
                else:
                    failed_count += 1
                    logger.warning(f" Failed to send report to {user['email']}")
                
            except Exception as e:
                failed_count += 1
                logger.error(f" Error sending report to user {user.get('user_id')}: {e}")
        
        # Update last sent timestamp
        await system_repo.update_portfolio_report_last_sent(datetime.now())
        
        # Calculate duration
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        logger.info("=" * 70)
        logger.info(" PORTFOLIO REPORT JOB COMPLETED")
        logger.info(f"Reports sent: {sent_count}")
        logger.info(f"Failed: {failed_count}")
        logger.info(f"Total users: {len(users_with_reports)}")
        logger.info(f"Duration: {duration:.2f} seconds")
        logger.info("=" * 70)
        
    except Exception as e:
        logger.error(f" Portfolio report job failed: {e}", exc_info=True)


async def send_single_user_report(db_pool: asyncpg.Pool, user_id: str):
    """
    Send portfolio report to a specific user (on-demand)
    
    Args:
        db_pool: Database connection pool
        user_id: User UUID
    """
    try:
        logger.info(f" Sending portfolio report to user: {user_id}")
        
        # Get user
        user_repo = UserRepository(db_pool)
        user = await user_repo.get_user_by_id(user_id)
        
        # Get portfolio data
        portfolio_service = PortfolioService(db_pool)
        portfolio_data = await portfolio_service.get_user_portfolio(user_id)
        
        # Send report
        email_service = EmailService(db_pool)
        success = await email_service.send_portfolio_report_email(user, portfolio_data)
        
        if success:
            logger.info(f" Report sent to {user['email']}")
        else:
            logger.warning(f" Failed to send report to {user['email']}")
        
        return success
        
    except Exception as e:
        logger.error(f" Failed to send report to user {user_id}: {e}")
        raise

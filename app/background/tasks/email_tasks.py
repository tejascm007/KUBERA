"""
Background Email Tasks
Async tasks for sending emails without blocking main thread
"""

import logging
import asyncio
from typing import Dict, Any, List

from app.services.email_service import EmailService
from app.db.database import get_db_pool

logger = logging.getLogger(__name__)


async def send_email_async(email_type: str, recipient: str, **kwargs):
    """
    Send email asynchronously
    
    Args:
        email_type: Type of email to send
        recipient: Recipient email
        **kwargs: Additional parameters for email
    """
    try:
        db_pool = await get_db_pool()
        email_service = EmailService(db_pool)
        
        if email_type == "welcome":
            await email_service.send_welcome_email(kwargs.get('user'))
        
        elif email_type == "password_changed":
            await email_service.send_password_changed_email(kwargs.get('user'))
        
        elif email_type == "account_deactivated":
            await email_service.send_account_deactivated_email(
                kwargs.get('user'),
                kwargs.get('reason')
            )
        
        elif email_type == "rate_limit_violation":
            await email_service.send_rate_limit_violation_email(
                kwargs.get('user_id'),
                kwargs.get('violation_type'),
                kwargs.get('limit')
            )
        
        logger.info(f" Email sent: {email_type} to {recipient}")
        
    except Exception as e:
        logger.error(f" Failed to send email {email_type} to {recipient}: {e}")


async def send_bulk_emails_async(email_type: str, recipients: List[Dict], **kwargs):
    """
    Send bulk emails asynchronously
    
    Args:
        email_type: Type of email to send
        recipients: List of recipient dicts
        **kwargs: Additional parameters
    """
    tasks = []
    
    for recipient in recipients:
        task = send_email_async(email_type, recipient['email'], user=recipient, **kwargs)
        tasks.append(task)
    
    # Send in batches of 10
    batch_size = 10
    for i in range(0, len(tasks), batch_size):
        batch = tasks[i:i+batch_size]
        await asyncio.gather(*batch, return_exceptions=True)
        
        # Small delay between batches
        if i + batch_size < len(tasks):
            await asyncio.sleep(1)
    
    logger.info(f" Bulk email sent: {email_type} to {len(recipients)} recipients")

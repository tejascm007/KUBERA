"""
Email Service
Business logic for sending emails (15+ triggers)
"""

from typing import Dict, Any, List
import logging
import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from jinja2 import Template

from app.db.repositories.email_repository import EmailRepository
from app.db.repositories.user_repository import UserRepository
from app.core.config import settings

logger = logging.getLogger(__name__)


class EmailService:
    """Email sending service with 15+ triggers"""
    
    def __init__(self, db_pool):
        self.db = db_pool
        self.email_repo = EmailRepository(db_pool)
        self.user_repo = UserRepository(db_pool)
    
    # ========================================================================
    # CORE EMAIL SENDING
    # ========================================================================
    
    async def _send_email(
        self,
        recipient_email: str,
        subject: str,
        html_body: str,
        email_type: str
    ) -> bool:
        """
        Send email via SMTP
        
        Args:
            recipient_email: Recipient email
            subject: Email subject
            html_body: HTML email body
            email_type: Type of email (for logging)
        
        Returns:
            True if sent successfully
        """
        # Log email
        log_entry = await self.email_repo.log_email(recipient_email, email_type, subject)
        
        try:
            # Create message
            message = MIMEMultipart("alternative")
            message["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
            message["To"] = recipient_email
            message["Subject"] = subject
            
            # Attach HTML body
            html_part = MIMEText(html_body, "html")
            message.attach(html_part)
            
            # Send email
            await aiosmtplib.send(
                message,
                hostname=settings.SMTP_HOST,
                port=settings.SMTP_PORT,
                username=settings.SMTP_USER,
                password=settings.SMTP_PASSWORD,
                use_tls=settings.SMTP_TLS
            )
            
            # Mark as sent
            await self.email_repo.mark_email_sent(log_entry['log_id'])
            
            logger.info(f"Email sent to {recipient_email}: {email_type}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email to {recipient_email}: {e}")
            await self.email_repo.mark_email_failed(log_entry['log_id'], str(e))
            return False
    
    # ========================================================================
    # EMAIL TEMPLATES
    # ========================================================================
    
    def _get_base_template(self) -> str:
        """Base HTML template for all emails"""
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
                .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                .header { background: #1a73e8; color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0; }
                .content { background: #f9f9f9; padding: 30px; border-radius: 0 0 8px 8px; }
                .button { display: inline-block; padding: 12px 24px; background: #1a73e8; color: white; text-decoration: none; border-radius: 4px; margin: 20px 0; }
                .footer { text-align: center; margin-top: 20px; font-size: 12px; color: #666; }
                .otp-box { background: #fff; border: 2px dashed #1a73e8; padding: 20px; text-align: center; font-size: 32px; font-weight: bold; letter-spacing: 8px; margin: 20px 0; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>KUBERA</h1>
                    <p>Your Stock Analysis Companion</p>
                </div>
                <div class="content">
                    {{ content }}
                </div>
                <div class="footer">
                    <p>&copy; 2024 KUBERA. All rights reserved.</p>
                    <p>This is an automated email. Please do not reply.</p>
                </div>
            </div>
        </body>
        </html>
        """
    
    # ========================================================================
    # EMAIL TRIGGER 1: OTP VERIFICATION
    # ========================================================================
    
    async def send_otp_email(
        self,
        email: str,
        otp: str,
        purpose: str = "registration"
    ) -> bool:
        """Send OTP verification email"""
        
        purpose_text = {
            "registration": "complete your registration",
            "password_reset": "reset your password",
            "admin_login": "login to admin panel"
        }
        
        content = f"""
        <h2>Your OTP Code</h2>
        <p>Please use the following OTP to {purpose_text.get(purpose, 'verify your identity')}:</p>
        <div class="otp-box">{otp}</div>
        <p><strong>This OTP is valid for {settings.OTP_EXPIRE_MINUTES} minutes.</strong></p>
        <p>If you didn't request this OTP, please ignore this email.</p>
        """
        
        html_body = Template(self._get_base_template()).render(content=content)
        
        return await self._send_email(
            recipient_email=email,
            subject=f"Your KUBERA OTP: {otp}",
            html_body=html_body,
            email_type=f"otp_{purpose}"
        )
    
    # ========================================================================
    # EMAIL TRIGGER 2: WELCOME EMAIL
    # ========================================================================
    
    async def send_welcome_email(self, user: Dict[str, Any]) -> bool:
        """Send welcome email after registration"""
        
        content = f"""
        <h2>Welcome to KUBERA, {user['full_name']}!</h2>
        <p>Your account has been successfully created. We're excited to have you on board!</p>
        <h3>What you can do with KUBERA:</h3>
        <ul>
            <li>Analyze Indian stocks with AI-powered insights</li>
            <li>Track your portfolio in real-time</li>
            <li>Get comprehensive fundamental and technical analysis</li>
            <li>Access news and sentiment analysis</li>
            <li>Generate beautiful visualizations</li>
        </ul>
        <p>Get started by creating your first chat and asking about any Indian stock!</p>
        <a href="#" class="button">Start Analyzing</a>
        """
        
        html_body = Template(self._get_base_template()).render(content=content)
        
        return await self._send_email(
            recipient_email=user['email'],
            subject="Welcome to KUBERA - Your Stock Analysis Journey Begins!",
            html_body=html_body,
            email_type="welcome"
        )
    
    # ========================================================================
    # EMAIL TRIGGER 3: PASSWORD CHANGED
    # ========================================================================
    
    async def send_password_changed_email(self, user: Dict[str, Any]) -> bool:
        """Send confirmation after password change"""
        
        content = f"""
        <h2>Password Changed Successfully</h2>
        <p>Hi {user['full_name']},</p>
        <p>Your KUBERA account password has been changed successfully.</p>
        <p><strong>If you didn't make this change, please contact us immediately.</strong></p>
        <p>For security reasons, you've been logged out from all devices. Please login again with your new password.</p>
        """
        
        html_body = Template(self._get_base_template()).render(content=content)
        
        return await self._send_email(
            recipient_email=user['email'],
            subject="KUBERA - Password Changed",
            html_body=html_body,
            email_type="password_changed"
        )
    
    # ========================================================================
    # EMAIL TRIGGER 4: ACCOUNT DEACTIVATED
    # ========================================================================
    
    async def send_account_deactivated_email(
        self,
        user: Dict[str, Any],
        reason: str = None
    ) -> bool:
        """Send notification when account is deactivated"""
        
        content = f"""
        <h2>Account Deactivated</h2>
        <p>Hi {user['full_name']},</p>
        <p>Your KUBERA account has been deactivated.</p>
        {f"<p><strong>Reason:</strong> {reason}</p>" if reason else ""}
        <p>If you believe this is a mistake, please contact our support team.</p>
        """
        
        html_body = Template(self._get_base_template()).render(content=content)
        
        return await self._send_email(
            recipient_email=user['email'],
            subject="KUBERA - Account Deactivated",
            html_body=html_body,
            email_type="account_deactivated"
        )
    
    # ========================================================================
    # EMAIL TRIGGER 5: ACCOUNT REACTIVATED
    # ========================================================================
    
    async def send_account_reactivated_email(self, user: Dict[str, Any]) -> bool:
        """Send notification when account is reactivated"""
        
        content = f"""
        <h2>Account Reactivated!</h2>
        <p>Hi {user['full_name']},</p>
        <p>Great news! Your KUBERA account has been reactivated.</p>
        <p>You can now login and continue using all features.</p>
        <a href="#" class="button">Login Now</a>
        """
        
        html_body = Template(self._get_base_template()).render(content=content)
        
        return await self._send_email(
            recipient_email=user['email'],
            subject="KUBERA - Account Reactivated",
            html_body=html_body,
            email_type="account_reactivated"
        )
    
    # ========================================================================
    # EMAIL TRIGGER 6-9: RATE LIMIT VIOLATIONS
    # ========================================================================
    
    async def send_rate_limit_violation_email(
        self,
        user_id: str,
        violation_type: str,
        limit: int
    ) -> bool:
        """Send notification for rate limit violation"""
        
        user = await self.user_repo.get_user_by_id(user_id)
        
        # Check if user has rate limit notifications enabled
        preferences = await self.email_repo.get_email_preferences(user_id)
        if not preferences or not preferences.get('rate_limit_notifications'):
            return False
        
        violation_messages = {
            "burst": f"You've exceeded the burst limit of {limit} prompts per minute.",
            "per_chat": f"This chat has reached its maximum limit of {limit} prompts.",
            "hourly": f"You've reached the hourly limit of {limit} prompts.",
            "daily": f"You've reached the daily limit of {limit} prompts for today."
        }
        
        content = f"""
        <h2>Rate Limit Reached</h2>
        <p>Hi {user['full_name']},</p>
        <p>{violation_messages.get(violation_type)}</p>
        <p>Please wait for the limit to reset before sending more prompts.</p>
        <p><strong>Why do we have rate limits?</strong></p>
        <p>Rate limits help us provide a fair and stable service for all users.</p>
        """
        
        html_body = Template(self._get_base_template()).render(content=content)
        
        return await self._send_email(
            recipient_email=user['email'],
            subject=f"KUBERA - Rate Limit {violation_type.title()} Reached",
            html_body=html_body,
            email_type=f"rate_limit_{violation_type}"
        )
    
    # ========================================================================
    # EMAIL TRIGGER 10: PORTFOLIO REPORT (DAILY/WEEKLY/MONTHLY)
    # ========================================================================
    
    async def send_portfolio_report_email(
        self,
        user: Dict[str, Any],
        portfolio_data: Dict[str, Any]
    ) -> bool:
        """Send portfolio performance report"""
        
        # Check if user has portfolio reports enabled
        preferences = await self.email_repo.get_email_preferences(user['user_id'])
        if not preferences or not preferences.get('portfolio_reports'):
            return False
        
        summary = portfolio_data.get('summary', {})
        entries = portfolio_data.get('portfolio', [])
        
        # Build portfolio table
        portfolio_rows = ""
        for entry in entries:
            gain_loss_color = "green" if entry.get('gain_loss', 0) >= 0 else "red"
            portfolio_rows += f"""
            <tr>
                <td>{entry['stock_symbol']}</td>
                <td>{entry['quantity']}</td>
                <td>₹{entry['buy_price']:.2f}</td>
                <td>₹{entry.get('current_price', 0):.2f}</td>
                <td style="color: {gain_loss_color};">₹{entry.get('gain_loss', 0):.2f} ({entry.get('gain_loss_percent', 0):.2f}%)</td>
            </tr>
            """
        
        total_gain_color = "green" if summary.get('total_gain_loss', 0) >= 0 else "red"
        
        content = f"""
        <h2>Your Portfolio Report</h2>
        <p>Hi {user['full_name']},</p>
        <p>Here's your portfolio performance summary:</p>
        
        <h3>Summary</h3>
        <ul>
            <li><strong>Total Invested:</strong> ₹{summary.get('total_invested', 0):,.2f}</li>
            <li><strong>Current Value:</strong> ₹{summary.get('current_value', 0):,.2f}</li>
            <li><strong>Total Gain/Loss:</strong> <span style="color: {total_gain_color};">₹{summary.get('total_gain_loss', 0):,.2f} ({summary.get('total_gain_loss_percent', 0):.2f}%)</span></li>
            <li><strong>Total Holdings:</strong> {summary.get('total_entries', 0)} stocks</li>
        </ul>
        
        <h3>Holdings</h3>
        <table style="width: 100%; border-collapse: collapse;">
            <thead>
                <tr style="background: #f0f0f0;">
                    <th style="padding: 8px; text-align: left;">Stock</th>
                    <th style="padding: 8px; text-align: left;">Qty</th>
                    <th style="padding: 8px; text-align: left;">Buy Price</th>
                    <th style="padding: 8px; text-align: left;">Current</th>
                    <th style="padding: 8px; text-align: left;">Gain/Loss</th>
                </tr>
            </thead>
            <tbody>
                {portfolio_rows}
            </tbody>
        </table>
        
        <p><small>Last updated: {summary.get('last_updated', 'N/A')}</small></p>
        """
        
        html_body = Template(self._get_base_template()).render(content=content)
        
        return await self._send_email(
            recipient_email=user['email'],
            subject="KUBERA - Your Portfolio Report",
            html_body=html_body,
            email_type="portfolio_report"
        )
    
    # ========================================================================
    # EMAIL TRIGGER 11: SYSTEM STATUS CHANGE
    # ========================================================================
    
    async def send_system_status_email(
        self,
        status: str,
        reason: str = None
    ) -> bool:
        """Send system status notification to all users"""
        
        # Get all users with system notifications enabled
        users = await self.email_repo.get_users_with_preference('system_notifications', True)
        
        status_messages = {
            "stopped": "The system is currently under maintenance.",
            "running": "The system is now operational.",
            "maintenance": "Scheduled maintenance is in progress."
        }
        
        for user in users:
            content = f"""
            <h2>System Status Update</h2>
            <p>Hi {user['full_name']},</p>
            <p><strong>Status:</strong> {status.upper()}</p>
            <p>{status_messages.get(status)}</p>
            {f"<p><strong>Reason:</strong> {reason}</p>" if reason else ""}
            <p>We apologize for any inconvenience.</p>
            """
            
            html_body = Template(self._get_base_template()).render(content=content)
            
            await self._send_email(
                recipient_email=user['email'],
                subject=f"KUBERA - System Status: {status.title()}",
                html_body=html_body,
                email_type="system_status"
            )
        
        return True
    
    # ========================================================================
    # EMAIL TRIGGER 12: USERNAME CHANGED
    # ========================================================================
    
    async def send_username_changed_email(
        self,
        user: Dict[str, Any],
        old_username: str,
        new_username: str
    ) -> bool:
        """Send notification when username is changed"""
        
        content = f"""
        <h2>Username Changed</h2>
        <p>Hi {user['full_name']},</p>
        <p>Your username has been changed successfully.</p>
        <p><strong>Old Username:</strong> {old_username}</p>
        <p><strong>New Username:</strong> {new_username}</p>
        <p>If you didn't make this change, please contact us immediately.</p>
        """
        
        html_body = Template(self._get_base_template()).render(content=content)
        
        return await self._send_email(
            recipient_email=user['email'],
            subject="KUBERA - Username Changed",
            html_body=html_body,
            email_type="username_changed"
        )
    
    # ========================================================================
    # EMAIL TRIGGER 13: SECURITY ALERT
    # ========================================================================
    
    async def send_security_alert_email(
        self,
        user: Dict[str, Any],
        alert_type: str,
        details: str
    ) -> bool:
        """Send security alert"""
        
        # Check if user has security alerts enabled
        preferences = await self.email_repo.get_email_preferences(user['user_id'])
        if not preferences or not preferences.get('security_alerts'):
            return False
        
        content = f"""
        <h2>Security Alert</h2>
        <p>Hi {user['full_name']},</p>
        <p>We detected unusual activity on your account.</p>
        <p><strong>Alert Type:</strong> {alert_type}</p>
        <p><strong>Details:</strong> {details}</p>
        <p>If this was you, you can safely ignore this email. Otherwise, please secure your account immediately.</p>
        <a href="#" class="button">Review Activity</a>
        """
        
        html_body = Template(self._get_base_template()).render(content=content)
        
        return await self._send_email(
            recipient_email=user['email'],
            subject="KUBERA - Security Alert",
            html_body=html_body,
            email_type="security_alert"
        )

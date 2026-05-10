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
        """Send portfolio performance report — premium HTML, no attachments"""
        from datetime import datetime as _dt

        summary = portfolio_data.get('summary', {})
        entries = portfolio_data.get('portfolio', [])

        report_date = _dt.now().strftime("%d %b %Y")

        # ── Summary numbers ───────────────────────────────────────────────────
        total_invested      = summary.get('total_invested', 0)
        current_value       = summary.get('current_value', 0)
        total_gain_loss     = summary.get('total_gain_loss', 0)
        gain_loss_pct       = summary.get('total_gain_loss_percent', 0)
        total_entries       = summary.get('total_entries', 0)

        gain_color   = "#16a34a" if total_gain_loss >= 0 else "#dc2626"
        gain_bg      = "#f0fdf4" if total_gain_loss >= 0 else "#fef2f2"
        gain_symbol  = "▲" if total_gain_loss >= 0 else "▼"

        # ── Holdings rows ─────────────────────────────────────────────────────
        if entries:
            holdings_rows = ""
            for i, e in enumerate(entries):
                gl       = e.get('gain_loss', 0)
                gl_pct   = e.get('gain_loss_percent', 0)
                gl_color = "#16a34a" if gl >= 0 else "#dc2626"
                row_bg   = "#ffffff" if i % 2 == 0 else "#f8fafc"
                holdings_rows += f"""
                <tr>
                  <td style="padding:10px 12px;border-bottom:1px solid #e2e8f0;background:{row_bg};font-weight:600;color:#1e293b;">{e.get('stock_symbol','—')}</td>
                  <td style="padding:10px 12px;border-bottom:1px solid #e2e8f0;background:{row_bg};color:#475569;">{e.get('quantity','—')}</td>
                  <td style="padding:10px 12px;border-bottom:1px solid #e2e8f0;background:{row_bg};color:#475569;">₹{float(e.get('buy_price',0)):,.2f}</td>
                  <td style="padding:10px 12px;border-bottom:1px solid #e2e8f0;background:{row_bg};color:#475569;">₹{float(e.get('current_price',0)):,.2f}</td>
                  <td style="padding:10px 12px;border-bottom:1px solid #e2e8f0;background:{row_bg};color:{gl_color};font-weight:600;">₹{float(gl):,.2f}<br><span style="font-size:11px;">({float(gl_pct):+.2f}%)</span></td>
                </tr>"""
            holdings_section = f"""
            <h3 style="margin:32px 0 12px;font-size:16px;color:#1e293b;font-family:Arial,sans-serif;">Holdings</h3>
            <table width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;border-radius:8px;overflow:hidden;border:1px solid #e2e8f0;">
              <thead>
                <tr style="background:#1e293b;">
                  <th style="padding:10px 12px;text-align:left;color:#94a3b8;font-size:12px;font-weight:600;font-family:Arial,sans-serif;">SYMBOL</th>
                  <th style="padding:10px 12px;text-align:left;color:#94a3b8;font-size:12px;font-weight:600;font-family:Arial,sans-serif;">QTY</th>
                  <th style="padding:10px 12px;text-align:left;color:#94a3b8;font-size:12px;font-weight:600;font-family:Arial,sans-serif;">BUY PRICE</th>
                  <th style="padding:10px 12px;text-align:left;color:#94a3b8;font-size:12px;font-weight:600;font-family:Arial,sans-serif;">CURRENT</th>
                  <th style="padding:10px 12px;text-align:left;color:#94a3b8;font-size:12px;font-weight:600;font-family:Arial,sans-serif;">GAIN / LOSS</th>
                </tr>
              </thead>
              <tbody>{holdings_rows}</tbody>
            </table>"""
        else:
            holdings_section = """
            <p style="color:#64748b;font-style:italic;margin-top:24px;font-family:Arial,sans-serif;">
              No portfolio entries found. Add stocks in your KUBERA portfolio to see them here.
            </p>"""

        html_body = f"""<!DOCTYPE html>
<html lang="en">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>KUBERA Portfolio Report</title></head>
<body style="margin:0;padding:0;background:#f1f5f9;font-family:Arial,sans-serif;">

  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f1f5f9;padding:32px 0;">
    <tr><td align="center">
      <table width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;">

        <!-- HEADER -->
        <tr><td style="background:#0f172a;border-radius:12px 12px 0 0;padding:32px 40px;">
          <table width="100%" cellpadding="0" cellspacing="0">
            <tr>
              <td>
                <div style="font-size:24px;font-weight:800;color:#ffffff;letter-spacing:2px;">KUBERA</div>
                <div style="font-size:12px;color:#64748b;margin-top:4px;letter-spacing:1px;">YOUR STOCK ANALYSIS COMPANION</div>
              </td>
              <td align="right">
                <div style="background:#1e293b;border-radius:8px;padding:8px 14px;display:inline-block;">
                  <div style="font-size:11px;color:#64748b;">Portfolio Report</div>
                  <div style="font-size:13px;color:#e2e8f0;font-weight:600;">{report_date}</div>
                </div>
              </td>
            </tr>
          </table>
        </td></tr>

        <!-- BODY -->
        <tr><td style="background:#ffffff;padding:32px 40px;border-radius:0 0 12px 12px;">

          <p style="margin:0 0 24px;color:#475569;font-size:15px;">
            Hi <strong style="color:#1e293b;">{user.get('full_name','Investor')}</strong>,<br>
            Here is your portfolio performance summary for <strong>{report_date}</strong>.
          </p>

          <!-- SUMMARY CARDS -->
          <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:8px;">
            <tr>
              <td width="30%" style="padding:4px;">
                <div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:10px;padding:16px;text-align:center;">
                  <div style="font-size:11px;color:#64748b;font-weight:600;letter-spacing:0.5px;margin-bottom:6px;">INVESTED</div>
                  <div style="font-size:18px;font-weight:700;color:#1e293b;">₹{float(total_invested):,.0f}</div>
                </div>
              </td>
              <td width="4%"></td>
              <td width="30%" style="padding:4px;">
                <div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:10px;padding:16px;text-align:center;">
                  <div style="font-size:11px;color:#64748b;font-weight:600;letter-spacing:0.5px;margin-bottom:6px;">CURRENT VALUE</div>
                  <div style="font-size:18px;font-weight:700;color:#1e293b;">₹{float(current_value):,.0f}</div>
                </div>
              </td>
              <td width="4%"></td>
              <td width="32%" style="padding:4px;">
                <div style="background:{gain_bg};border:1px solid {gain_color}33;border-radius:10px;padding:16px;text-align:center;">
                  <div style="font-size:11px;color:#64748b;font-weight:600;letter-spacing:0.5px;margin-bottom:6px;">TOTAL GAIN / LOSS</div>
                  <div style="font-size:18px;font-weight:700;color:{gain_color};">{gain_symbol} ₹{abs(float(total_gain_loss)):,.0f}</div>
                  <div style="font-size:12px;color:{gain_color};margin-top:2px;">{float(gain_loss_pct):+.2f}%</div>
                </div>
              </td>
            </tr>
          </table>

          <p style="text-align:center;margin:8px 0 4px;font-size:12px;color:#94a3b8;">
            {total_entries} stock{'s' if total_entries != 1 else ''} in portfolio
          </p>

          <!-- HOLDINGS TABLE -->
          {holdings_section}

          <!-- FOOTER NOTE -->
          <p style="margin-top:32px;font-size:12px;color:#94a3b8;border-top:1px solid #e2e8f0;padding-top:20px;">
            This report is generated automatically by KUBERA. Prices shown may be delayed.<br>
            This is not financial advice. Please do your own research before making investment decisions.
          </p>

        </td></tr>

        <!-- BOTTOM BAR -->
        <tr><td style="padding:20px;text-align:center;">
          <p style="margin:0;font-size:11px;color:#94a3b8;">© 2025 KUBERA · All rights reserved · This is an automated email, please do not reply.</p>
        </td></tr>

      </table>
    </td></tr>
  </table>
</body>
</html>"""

        return await self._send_email(
            recipient_email=user['email'],
            subject=f"KUBERA Portfolio Report — {report_date}",
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


# ==========================================
# FORGOT PASSWORD EMAIL TEMPLATES
# ==========================================

async def send_forgot_password_email(
    self,
    email: str,
    full_name: str,
    otp: str
) -> bool:
    """Send forgot password OTP email"""
    
    subject = "Reset Your KUBERA Password"
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: 'Lato', Arial, sans-serif; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background-color: #1A1A1A; color: white; padding: 20px; text-align: center; }}
            .content {{ padding: 20px; background-color: #FAFBFC; }}
            .otp-box {{ 
                background-color: #ece3fa; 
                padding: 20px; 
                text-align: center; 
                font-size: 24px; 
                font-weight: bold; 
                letter-spacing: 2px;
                margin: 20px 0;
                border-radius: 8px;
            }}
            .warning {{ color: #d32f2f; font-size: 14px; margin-top: 10px; }}
            .footer {{ text-align: center; font-size: 12px; color: #666; margin-top: 20px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>KUBERA</h1>
                <p>Password Reset Request</p>
            </div>
            
            <div class="content">
                <p>Hi {full_name},</p>
                
                <p>We received a request to reset your KUBERA password. Use the OTP below to complete the process.</p>
                
                <div class="otp-box">{otp}</div>
                
                <p><strong>This OTP is valid for 10 minutes.</strong></p>
                
                <p>Steps to reset your password:</p>
                <ol>
                    <li>Enter your email address</li>
                    <li>Enter the OTP above</li>
                    <li>Create a new password</li>
                    <li>Click confirm</li>
                </ol>
                
                <div class="warning">
                    ⚠️ <strong>Security Note:</strong> If you didn't request this password reset, please ignore this email. Your account remains secure.
                </div>
                
                <p>Questions? Contact our support team.</p>
                
                <div class="footer">
                    <p>© 2025 KUBERA Investment Chatbot. All rights reserved.</p>
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    
    return await self.send_email(
        recipient_email=email,
        subject=subject,
        html_content=html_content,
        email_type="forgot_password"
    )


async def send_password_reset_confirmation(
    self,
    email: str,
    full_name: str
) -> bool:
    """Send password reset confirmation email"""
    
    subject = "Your Password Has Been Reset"
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: 'Lato', Arial, sans-serif; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background-color: #1A1A1A; color: white; padding: 20px; text-align: center; }}
            .content {{ padding: 20px; background-color: #FAFBFC; }}
            .success {{ color: #2e7d32; font-size: 16px; margin: 20px 0; }}
            .footer {{ text-align: center; font-size: 12px; color: #666; margin-top: 20px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>KUBERA</h1>
                <p>Password Reset Successful</p>
            </div>
            
            <div class="content">
                <p>Hi {full_name},</p>
                
                <p class="success">✓ Your password has been successfully reset!</p>
                
                <p>You can now login with your new password. Your session was logged out for security.</p>
                
                <p>If this wasn't you, please:</p>
                <ol>
                    <li>Reset your password immediately</li>
                    <li>Contact our support team</li>
                </ol>
                
                <p><strong>Login here:</strong> https://kubera.app/login</p>
                
                <div class="footer">
                    <p>© 2025 KUBERA Investment Chatbot. All rights reserved.</p>
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    
    return await self.send_email(
        recipient_email=email,
        subject=subject,
        html_content=html_content,
        email_type="password_reset_confirmation"
    )

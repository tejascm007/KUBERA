"""
Email HTML Templates
15+ email templates for various triggers
"""

from typing import Dict, Any
from datetime import datetime


def get_base_template() -> str:
    """Base HTML template wrapper"""
    return """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {{
            font-family: Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
            border-radius: 10px 10px 0 0;
        }}
        .content {{
            background: #f9f9f9;
            padding: 30px;
            border-radius: 0 0 10px 10px;
        }}
        .button {{
            display: inline-block;
            padding: 12px 30px;
            background: #667eea;
            color: white;
            text-decoration: none;
            border-radius: 5px;
            margin: 20px 0;
        }}
        .otp-box {{
            background: white;
            border: 2px dashed #667eea;
            padding: 20px;
            text-align: center;
            font-size: 32px;
            font-weight: bold;
            letter-spacing: 8px;
            margin: 20px 0;
            border-radius: 5px;
        }}
        .footer {{
            text-align: center;
            margin-top: 30px;
            color: #666;
            font-size: 12px;
        }}
        .info-box {{
            background: white;
            padding: 15px;
            border-left: 4px solid #667eea;
            margin: 15px 0;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>KUBERA</h1>
        <p>AI-Powered Stock Analysis Platform</p>
    </div>
    <div class="content">
        {content}
    </div>
    <div class="footer">
        <p>© 2025 KUBERA. All rights reserved.</p>
        <p>This is an automated email. Please do not reply.</p>
    </div>
</body>
</html>
"""


def otp_registration_email(otp: str, expiry_minutes: int) -> str:
    """OTP for registration"""
    content = f"""
        <h2>Welcome to KUBERA!</h2>
        <p>Thank you for registering with KUBERA, India's AI-powered stock analysis platform.</p>
        <p>Your One-Time Password (OTP) for registration is:</p>
        <div class="otp-box">{otp}</div>
        <div class="info-box">
            <strong>Valid for {expiry_minutes} minutes</strong><br>
            <strong>Keep this OTP confidential</strong>
        </div>
        <p>If you didn't request this OTP, please ignore this email.</p>
    """
    return get_base_template().format(content=content)


def otp_password_reset_email(otp: str, expiry_minutes: int) -> str:
    """OTP for password reset"""
    content = f"""
        <h2>Password Reset Request</h2>
        <p>We received a request to reset your password.</p>
        <p>Your One-Time Password (OTP) is:</p>
        <div class="otp-box">{otp}</div>
        <div class="info-box">
            <strong>Valid for {expiry_minutes} minutes</strong><br>
            <strong>Keep this OTP confidential</strong>
        </div>
        <p>If you didn't request a password reset, please ignore this email and your password will remain unchanged.</p>
    """
    return get_base_template().format(content=content)


def otp_admin_login_email(otp: str, expiry_minutes: int) -> str:
    """OTP for admin login"""
    content = f"""
        <h2>Admin Login Verification</h2>
        <p>Your admin login OTP is:</p>
        <div class="otp-box">{otp}</div>
        <div class="info-box">
            <strong>Valid for {expiry_minutes} minutes</strong><br>
            <strong>ADMIN ACCESS - Keep confidential</strong>
        </div>
        <p>If you didn't attempt to login, please contact security immediately.</p>
    """
    return get_base_template().format(content=content)


def welcome_email(full_name: str) -> str:
    """Welcome email after registration"""
    content = f"""
        <h2>Welcome aboard, {full_name}!</h2>
        <p>Your account has been successfully created. You're now part of India's most advanced AI-powered stock analysis platform.</p>
        
        <div class="info-box">
            <h3>What you can do with KUBERA:</h3>
            <ul>
                <li>Analyze Indian stocks (NSE/BSE) with AI</li>
                <li>Track your portfolio with live prices</li>
                <li>Get technical analysis & insights</li>
                <li>Real-time news & sentiment analysis</li>
                <li>Beautiful charts & visualizations</li>
            </ul>
        </div>
        
        <a href="https://kubera.ai/dashboard" class="button">Go to Dashboard</a>
        
        <p>Happy investing!</p>
    """
    return get_base_template().format(content=content)


def password_changed_email(full_name: str) -> str:
    """Password changed confirmation"""
    content = f"""
        <h2>Password Changed Successfully</h2>
        <p>Hi {full_name},</p>
        <p>Your password has been changed successfully.</p>
        
        <div class="info-box">
            <strong>Changed at:</strong> {datetime.now().strftime('%d %B %Y, %H:%M IST')}<br>
            <strong>Security Tip:</strong> Never share your password with anyone
        </div>
        
        <p>If you didn't make this change, please contact our support team immediately.</p>
    """
    return get_base_template().format(content=content)


def account_deactivated_email(full_name: str, reason: str) -> str:
    """Account deactivated notification"""
    content = f"""
        <h2>Account Deactivated</h2>
        <p>Hi {full_name},</p>
        <p>Your KUBERA account has been deactivated.</p>
        
        <div class="info-box">
            <strong>Reason:</strong> {reason}<br>
            <strong>Date:</strong> {datetime.now().strftime('%d %B %Y, %H:%M IST')}
        </div>
        
        <p>You can reactivate your account anytime by logging in.</p>
        <p>If you have questions, please contact our support team.</p>
    """
    return get_base_template().format(content=content)


def rate_limit_burst_exceeded_email(full_name: str, limit: int) -> str:
    """Burst rate limit exceeded"""
    content = f"""
        <h2>Rate Limit Notification</h2>
        <p>Hi {full_name},</p>
        <p>You've exceeded the burst rate limit of <strong>{limit} prompts per minute</strong>.</p>
        
        <div class="info-box">
            <strong>What this means:</strong> You're sending prompts too quickly<br>
            <strong>Solution:</strong> Please wait a minute before sending more prompts
        </div>
        
        <p>This limit helps ensure optimal performance for all users.</p>
    """
    return get_base_template().format(content=content)


def rate_limit_hourly_exceeded_email(full_name: str, limit: int) -> str:
    """Hourly rate limit exceeded"""
    content = f"""
        <h2>Rate Limit Notification</h2>
        <p>Hi {full_name},</p>
        <p>You've reached the hourly limit of <strong>{limit} prompts</strong>.</p>
        
        <div class="info-box">
            <strong>Your limit resets:</strong> In the next hour<br>
            <strong>Consider:</strong> Upgrading to premium for higher limits
        </div>
        
        <p>Thank you for your understanding!</p>
    """
    return get_base_template().format(content=content)


def rate_limit_daily_exceeded_email(full_name: str, limit: int) -> str:
    """Daily rate limit exceeded"""
    content = f"""
        <h2>Daily Limit Reached</h2>
        <p>Hi {full_name},</p>
        <p>You've reached your daily limit of <strong>{limit} prompts</strong>.</p>
        
        <div class="info-box">
            <strong>Your limit resets:</strong> Tomorrow at 00:00 IST<br>
            <strong>Upgrade to Premium:</strong> Get 10x higher limits!
        </div>
        
        <a href="https://kubera.ai/pricing" class="button">View Plans</a>
    """
    return get_base_template().format(content=content)


def portfolio_report_email(full_name: str, portfolio_data: Dict[str, Any]) -> str:
    """Portfolio performance report"""
    total_invested = portfolio_data.get('total_invested', 0)
    current_value = portfolio_data.get('current_value', 0)
    total_gain_loss = portfolio_data.get('total_gain_loss', 0)
    gain_loss_percent = portfolio_data.get('gain_loss_percent', 0)
    
    from app.utils.formatters import format_inr, format_percentage
    
    gain_loss_color = 'green' if total_gain_loss >= 0 else 'red'
    
    content = f"""
        <h2>Your Portfolio Report</h2>
        <p>Hi {full_name},</p>
        <p>Here's your portfolio performance summary:</p>
        
        <div class="info-box">
            <strong>Total Invested:</strong> {format_inr(total_invested)}<br>
            <strong>Current Value:</strong> {format_inr(current_value)}<br>
            <strong style="color: {gain_loss_color};">Gain/Loss:</strong> 
            <span style="color: {gain_loss_color};">{format_inr(total_gain_loss)} ({format_percentage(gain_loss_percent)})</span>
        </div>
        
        <p><strong>Total Holdings:</strong> {len(portfolio_data.get('portfolio', []))} stocks</p>
        
        <a href="https://kubera.ai/portfolio" class="button">View Full Portfolio</a>
        
        <p>Keep investing wisely!</p>
    """
    return get_base_template().format(content=content)


def system_maintenance_email(full_name: str, start_time: str, end_time: str) -> str:
    """System maintenance notification"""
    content = f"""
        <h2>Scheduled Maintenance</h2>
        <p>Hi {full_name},</p>
        <p>KUBERA will undergo scheduled maintenance:</p>
        
        <div class="info-box">
            <strong>Start Time:</strong> {start_time}<br>
            <strong>End Time:</strong> {end_time}<br>
            <strong>Impact:</strong> Service will be temporarily unavailable
        </div>
        
        <p>We apologize for any inconvenience. We're working to improve your experience!</p>
    """
    return get_base_template().format(content=content)

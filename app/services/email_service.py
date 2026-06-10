import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from loguru import logger


def _get_smtp_config() -> dict:
    """
    Retrieve SMTP credentials from the DB settings table (global scope),
    falling back to environment variables, and finally to empty strings.
    This eliminates hardcoded credentials from the source code.
    """
    try:
        from app.services import db
        sender_email = (
            db.get_setting("smtp_email", user_id="global")
            or os.getenv("SMTP_EMAIL", "")
        )
        app_password = (
            db.get_setting("smtp_password", user_id="global")
            or os.getenv("SMTP_PASSWORD", "")
        )
        recipient_email = (
            db.get_setting("smtp_recipient", user_id="global")
            or os.getenv("SMTP_RECIPIENT", sender_email)
        )
        smtp_host = (
            db.get_setting("smtp_host", user_id="global")
            or os.getenv("SMTP_HOST", "smtp.gmail.com")
        )
        smtp_port = int(
            db.get_setting("smtp_port", user_id="global")
            or os.getenv("SMTP_PORT", "587")
        )
    except Exception as e:
        logger.warning(f"Could not load SMTP config from DB, using env fallback: {e}")
        sender_email = os.getenv("SMTP_EMAIL", "")
        app_password = os.getenv("SMTP_PASSWORD", "")
        recipient_email = os.getenv("SMTP_RECIPIENT", sender_email)
        smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
        smtp_port = int(os.getenv("SMTP_PORT", "587"))

    return {
        "sender_email": sender_email,
        "app_password": app_password,
        "recipient_email": recipient_email,
        "smtp_host": smtp_host,
        "smtp_port": smtp_port,
    }


def send_pipeline_email(
    task_id: str,
    state: int,
    progress: int,
    subject: str,
    status_msg: str,
    cdn_url: str = "",
    error_msg: str = "",
    user_id: str = "global"
) -> bool:
    """
    Sends an automated email notification about the MoneyPrinterTurbo task status.
    Uses Gmail SMTP with TLS. Credentials are sourced from DB settings or env vars.
    """
    smtp_cfg = _get_smtp_config()
    sender_email = smtp_cfg["sender_email"]
    app_password = smtp_cfg["app_password"]
    recipient_email = smtp_cfg["recipient_email"]
    smtp_host = smtp_cfg["smtp_host"]
    smtp_port = smtp_cfg["smtp_port"]

    if not sender_email or not app_password:
        logger.warning(
            f"Email notification skipped for task {task_id}: SMTP credentials not configured. "
            "Set smtp_email and smtp_password via the Admin Panel or SMTP_EMAIL/SMTP_PASSWORD env vars."
        )
        return False

    # Map numerical states to readable status strings
    status_name = "PENDING"
    if state == 1:
        status_name = "COMPLETED"
    elif state in [-1, 2]:
        status_name = "FAILED"
    elif state == 3:
        status_name = "STOPPED/PAUSED"
    elif state == 4:
        status_name = "PROCESSING"
        
    email_subject = f"MoneyPrinterTurbo Pipeline Run: {status_name} - Task {task_id[:8]}"
    
    # Compile HTML body report
    status_color = "#10b981" if state == 1 else "#ef4444" if state in [-1, 2] else "#f59e0b"
    
    html_content = f"""
    <html>
        <body style="font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; background-color: #f3f4f6; padding: 20px; color: #1f2937;">
            <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05); border: 1px solid #e5e7eb;">
                <!-- Header Banner -->
                <div style="background-color: #0b0f19; padding: 30px; text-align: center;">
                    <h1 style="color: #ffffff; margin: 0; font-size: 24px; font-weight: bold; letter-spacing: 0.5px;">🎬 Turbo Studio SaaS</h1>
                    <p style="color: #9ca3af; margin: 5px 0 0 0; font-size: 14px;">Automated Video Generation Pipeline</p>
                </div>
                
                <!-- Content Section -->
                <div style="padding: 30px;">
                    <div style="text-align: center; margin-bottom: 24px;">
                        <span style="display: inline-block; padding: 8px 16px; background-color: {status_color}; color: #ffffff; font-weight: bold; font-size: 14px; border-radius: 9999px; text-transform: uppercase;">
                            {status_name}
                        </span>
                    </div>
                    
                    <p style="font-size: 16px; line-height: 1.5; margin-top: 0;">Hello,</p>
                    <p style="font-size: 15px; line-height: 1.6;">
                        Your automated short video pipeline task has finished execution. Below is the detailed run summary report.
                    </p>
                    
                    <!-- Details Table -->
                    <table style="width: 100%; border-collapse: collapse; margin: 20px 0; font-size: 14px; border: 1px solid #e5e7eb; border-radius: 8px; overflow: hidden;">
                        <tr style="background-color: #f9fafb;">
                            <td style="padding: 12px; font-weight: bold; width: 35%; border-bottom: 1px solid #e5e7eb;">Task ID</td>
                            <td style="padding: 12px; border-bottom: 1px solid #e5e7eb; font-family: monospace;">{task_id}</td>
                        </tr>
                        <tr>
                            <td style="padding: 12px; font-weight: bold; border-bottom: 1px solid #e5e7eb;">Video Theme</td>
                            <td style="padding: 12px; border-bottom: 1px solid #e5e7eb; font-weight: 500;">{subject or 'N/A'}</td>
                        </tr>
                        <tr style="background-color: #f9fafb;">
                            <td style="padding: 12px; font-weight: bold; border-bottom: 1px solid #e5e7eb;">Run Status</td>
                            <td style="padding: 12px; border-bottom: 1px solid #e5e7eb;">{status_msg or 'No message provided'}</td>
                        </tr>
                        <tr>
                            <td style="padding: 12px; font-weight: bold; border-bottom: 1px solid #e5e7eb;">Clerk User ID</td>
                            <td style="padding: 12px; border-bottom: 1px solid #e5e7eb; font-family: monospace;">{user_id}</td>
                        </tr>
    """
    
    if state == 1 and cdn_url:
        html_content += f"""
                        <tr style="background-color: #ecfdf5;">
                            <td style="padding: 12px; font-weight: bold; border-bottom: 1px solid #e5e7eb; color: #065f46;">Cloud CDN URL</td>
                            <td style="padding: 12px; border-bottom: 1px solid #e5e7eb;">
                                <a href="{cdn_url}" target="_blank" style="color: #059669; font-weight: bold; text-decoration: underline;">Stream Video</a>
                            </td>
                        </tr>
        """
        
    if state in [-1, 2] and error_msg:
        html_content += f"""
                        <tr style="background-color: #fef2f2;">
                            <td style="padding: 12px; font-weight: bold; border-bottom: 1px solid #e5e7eb; color: #991b1b;">Error Details</td>
                            <td style="padding: 12px; border-bottom: 1px solid #e5e7eb; color: #dc2626; font-family: monospace; font-size: 12px;">{error_msg}</td>
                        </tr>
        """
        
    html_content += """
                    </table>
                    
                    <p style="font-size: 13px; color: #6b7280; line-height: 1.5; margin-top: 30px;">
                        This is an automated notification from your SaaS rendering server. Do not reply directly to this email.
                    </p>
                </div>
                
                <!-- Footer -->
                <div style="background-color: #f9fafb; padding: 20px; text-align: center; font-size: 12px; color: #9ca3af; border-top: 1px solid #e5e7eb;">
                    &copy; 2026 Turbo Studio Automation Services. All rights reserved.
                </div>
            </div>
        </body>
    </html>
    """
    
    # Build MIME message
    msg = MIMEMultipart('alternative')
    msg['Subject'] = email_subject
    msg['From'] = sender_email
    msg['To'] = recipient_email
    
    msg.attach(MIMEText(html_content, 'html'))
    
    try:
        logger.info(f"Sending email notification for task {task_id} to {recipient_email}...")
        # Connect to SMTP Server using STARTTLS
        server = smtplib.SMTP(smtp_host, smtp_port)
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(sender_email, app_password)
        server.sendmail(sender_email, [recipient_email], msg.as_string())
        server.close()
        logger.success(f"Email notification successfully sent to {recipient_email} for task {task_id}.")
        return True
    except Exception as smtp_err:
        logger.error(f"Failed to send email notification via SMTP: {smtp_err}")
        return False

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import current_app

def send_support_reply_email(recipient_email, subject, reply_body):
    """
    Sends a support reply email via SMTP using configuration from current_app.config.
    Returns: (success: bool, message: str, provider_msg_id: str or None)
    """
    mail_server = current_app.config.get('MAIL_SERVER', 'smtp.gmail.com')
    mail_port = current_app.config.get('MAIL_PORT', 587)
    mail_use_tls = current_app.config.get('MAIL_USE_TLS', True)
    mail_username = current_app.config.get('MAIL_USERNAME', '').strip()
    mail_password = current_app.config.get('MAIL_PASSWORD', '').strip()
    sender_email = current_app.config.get('MAIL_DEFAULT_SENDER', 'support@sparepro.local')

    # If SMTP credentials are not set in environment, return explicit failure message
    if not mail_username or not mail_password:
        return False, "SMTP configuration missing: MAIL_USERNAME and MAIL_PASSWORD environment variables are not set.", None

    try:
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = recipient_email
        msg['Subject'] = subject

        msg.attach(MIMEText(reply_body, 'plain'))

        server = smtplib.SMTP(mail_server, mail_port, timeout=10)
        if mail_use_tls:
            server.starttls()
        server.login(mail_username, mail_password)
        server.send_message(msg)
        server.quit()

        return True, "Email submitted successfully to SMTP server.", f"SMTP-{recipient_email}"
    except Exception as e:
        current_app.logger.error(f"SMTP sending error to {recipient_email}: {e}")
        return False, f"SMTP delivery failed: {str(e)}", None


def send_complaint_acknowledgement_email(recipient_email, complaint_ref, subject):
    """
    Sends an acknowledgement email to customer when a complaint/enquiry is submitted.
    Returns: (success: bool, message: str)
    """
    mail_server = current_app.config.get('MAIL_SERVER', 'smtp.gmail.com')
    mail_port = current_app.config.get('MAIL_PORT', 587)
    mail_use_tls = current_app.config.get('MAIL_USE_TLS', True)
    mail_username = current_app.config.get('MAIL_USERNAME', '').strip()
    mail_password = current_app.config.get('MAIL_PASSWORD', '').strip()
    sender_email = current_app.config.get('MAIL_DEFAULT_SENDER', 'support@sparepro.local')

    if not mail_username or not mail_password:
        return False, "SMTP configuration missing: MAIL_USERNAME and MAIL_PASSWORD environment variables are not set."

    try:
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = recipient_email
        msg['Subject'] = f"Enquiry Received [{complaint_ref}] - {subject}"

        body = (
            f"Dear Customer,\n\n"
            f"Thank you for contacting SparePro Support.\n"
            f"Your enquiry has been received successfully. Your Reference Number is {complaint_ref}.\n\n"
            f"Subject: {subject}\n\n"
            f"Our team will review your message and respond soon.\n\n"
            f"Regards,\nSparePro Support Team"
        )
        msg.attach(MIMEText(body, 'plain'))

        server = smtplib.SMTP(mail_server, mail_port, timeout=10)
        if mail_use_tls:
            server.starttls()
        server.login(mail_username, mail_password)
        server.send_message(msg)
        server.quit()

        return True, "Acknowledgement email sent successfully."
    except Exception as e:
        current_app.logger.error(f"Failed to send acknowledgement email to {recipient_email}: {e}")
        return False, f"SMTP delivery failed: {str(e)}"


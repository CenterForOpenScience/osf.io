import logging
import smtplib
from email.mime.text import MIMEText
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from website import settings

def send_email_over_smtp(to_addr, notification_type, context):
    """Send an email notification using SMTP. This is typically not used in productions as other 3rd party mail services
    are preferred. This is to be used for tests and on staging environments and special situations.

    Args:
        to_addr (str): The recipient's email address.
        notification_type (str): The subject of the notification.
        context (dict): The email content context.
    """
    if not settings.MAIL_SERVER:
        raise NotImplementedError('MAIL_SERVER is not set')
    if not settings.MAIL_USERNAME and settings.MAIL_PASSWORD:
        raise NotImplementedError('MAIL_USERNAME and MAIL_PASSWORD are required for STMP')

    msg = MIMEText(
        notification_type.template.format(**context),
        'html',
        _charset='utf-8'
    )

    with smtplib.SMTP(settings.MAIL_SERVER) as server:
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(settings.MAIL_USERNAME, settings.MAIL_PASSWORD)
        server.sendmail(
            settings.FROM_EMAIL,
            [to_addr],
            msg.as_string()
        )


def send_email_with_send_grid(to_addr, notification_type, context):
    """Send an email notification using SendGrid.

    Args:
        to_addr (str): The recipient's email address.
        notification_type (str): The subject of the notification.
        context (dict): The email content context.
    """
    if not settings.SENDGRID_API_KEY:
        raise NotImplementedError('SENDGRID_API_KEY is required for sendgrid notifications.')

    message = Mail(
        from_email=settings.FROM_EMAIL,
        to_emails=to_addr,
        subject=notification_type,
        html_content=context.get('message', '')
    )

    try:
        sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
        response = sg.send(message)
        if response.status_code not in (200, 201, 202):
            logging.error(f'SendGrid response error: {response.status_code}, body: {response.body}')
            response.raise_for_status()
        logging.info(f'Notification email sent to {to_addr} for {notification_type}.')
    except Exception as exc:
        logging.error(f'Failed to send email notification to {to_addr}: {exc}')
        raise exc

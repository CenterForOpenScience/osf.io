import logging
import smtplib
from email.mime.text import MIMEText

import waffle
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

from osf import features
from website import settings
from django.core.mail import EmailMessage, get_connection


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

    if waffle.switch_is_active(features.ENABLE_MAILHOG):
        send_to_mailhog(
            subject=notification_type.subject,
            message=notification_type.template.format(**context),
            to_email=to_addr,
            from_email=settings.MAIL_USERNAME,
        )
        return

    msg = MIMEText(
        notification_type.template.format(**context),
        'html',
        _charset='utf-8'
    )

    if notification_type.subject:
        msg['Subject'] = notification_type.subject.format(**context)

    with smtplib.SMTP(settings.MAIL_SERVER) as server:
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

def send_to_mailhog(subject, message, from_email, to_email, attachment_name=None, attachment_content=None):
    email = EmailMessage(
        subject=subject,
        body=message,
        from_email=from_email,
        to=[to_email],
        connection=get_connection(
            backend='django.core.mail.backends.smtp.EmailBackend',
            host=settings.MAILHOG_HOST,
            port=settings.MAILHOG_PORT,
            username='',
            password='',
            use_tls=False,
            use_ssl=False,
        )
    )
    email.content_subtype = 'html'

    if attachment_name and attachment_content:
        email.attach(attachment_name, attachment_content)

    email.send()

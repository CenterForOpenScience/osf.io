import logging

import waffle
from sendgrid import SendGridAPIClient, Personalization, To, Cc, Category, ReplyTo, Bcc
from sendgrid.helpers.mail import Mail

from osf import features
from website import settings
from django.core.mail import EmailMessage, get_connection


def send_email_over_smtp(to_email, notification_type, context, email_context):
    """Send an email notification using SMTP. This is typically not used in productions as other 3rd party mail services
    are preferred. This is to be used for tests and on staging environments and special situations.

    Args:
        to_addr (str): The recipient's email address.
        notification_type (str): The subject of the notification.
        context (dict): The email content context.
        email_context (dict): The email context for sending, such as header changes for BCC or reply-to
    """
    if not settings.MAIL_SERVER:
        raise NotImplementedError('MAIL_SERVER is not set')

    if waffle.switch_is_active(features.ENABLE_MAILHOG):
        host = settings.MAILHOG_HOST
        port = settings.MAILHOG_PORT
    else:
        host = settings.MAIL_SERVER
        port = settings.MAIL_PORT

    email = EmailMessage(
        subject=notification_type.subject.format(**context),
        body=notification_type.template.format(**context),
        from_email=settings.OSF_SUPPORT_EMAIL,
        to=[to_email],
        connection=get_connection(
            backend='django.core.mail.backends.smtp.EmailBackend',
            host=host,
            port=port,
            username=settings.MAIL_USERNAME,
            password=settings.MAIL_PASSWORD,
            use_tls=False,
            use_ssl=False,
        )
    )
    email.content_subtype = 'html'

    if email_context:
        attachment_name = email_context.get('attachment_name', None)
        attachment_content = email_context.get('attachment_content', None)
        if attachment_name and attachment_content:
            email.attach(attachment_name, attachment_content)

    email.send()

def send_email_with_send_grid(to_addr, notification_type, context, email_context):
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
    in_allowed_list = to_addr in settings.SENDGRID_EMAIL_WHITELIST
    if settings.SENDGRID_WHITELIST_MODE and not in_allowed_list:
        from framework.sentry import sentry

        sentry.log_message(
            f'SENDGRID_WHITELIST_MODE is True. Failed to send emails to non-whitelisted recipient {to_addr}.'
        )
        return False

    # Personalization to handle To, CC, and BCC sendgrid client concept
    personalization = Personalization()

    personalization.add_to(To(to_addr))

    if cc_addr := email_context.get('cc_addr'):
        if isinstance(cc_addr, str):
            cc_addr = [cc_addr]
        for email in cc_addr:
            personalization.add_cc(Cc(email))

    if bcc_addr := email_context.get('cc_addr'):
        if isinstance(bcc_addr, str):
            bcc_addr = [bcc_addr]
        for email in bcc_addr:
            personalization.add_bcc(Bcc(email))

    if reply_to := email_context.get('reply_to'):
        message.reply_to = ReplyTo(reply_to)

    message.add_personalization(personalization)

    if email_categories := email_context.get('email_categories'):
        message.add_category([Category(x) for x in email_categories])

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

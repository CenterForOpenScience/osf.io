import smtplib

from email.mime.text import MIMEText
from framework.tasks import celery
from website import settings  # TODO: Use framework's config module instead


@celery.task
def send_email(from_, to, subject, message):
    """Send email to specified destination.
    Email is sent from the email specified in FROM_EMAIL settings in the
    settings module.

    :param from_: A string, the sender email
    :param to: A string, the recipient
    :param subject: subject of email
    :param message: body of message

    :return: True if successful
    """
    msg = MIMEText(message, _charset='utf-8')
    msg['Subject'] = subject
    msg['From'] = from_
    msg['To'] = to

    s = smtplib.SMTP(settings.mail_server)
    s.ehlo()
    s.starttls()
    s.ehlo()
    s.login(settings.mail_username, settings.mail_password)
    s.sendmail(
        from_addr=from_,
        to_addrs=[to],
        msg=msg.as_string()
    )
    s.quit()
    return True

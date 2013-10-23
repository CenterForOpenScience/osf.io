import smtplib

from email.mime.text import MIMEText
from framework.tasks import celery
from website import settings  # TODO: Use framework's config module instead

@celery.task
def send_email(to=None, subject=None, message=None):
    """sends email from openscienceframework-noreply to specified destination

    :param to: string destination address
    :param subject: subject of email
    :param message: body of message

    :return: True if successful
    """
    fro = settings.FROM_EMAIL
    msg = MIMEText(message, _charset='utf-8')
    msg['Subject'] = subject
    msg['From'] = fro
    msg['To'] = to

    s = smtplib.SMTP(settings.mail_server)
    s.ehlo()
    s.starttls()
    s.ehlo()
    s.login(settings.mail_username, settings.mail_password)
    s.sendmail(
        from_addr=fro,
        to_addrs=[to],
        msg=msg.as_string()
    )
    s.quit()
    return True

import smtplib

from email.mime.text import MIMEText
from framework.celery.celery import celery

@celery.task
def send_email(to=None, subject=None, message=None):
    """sends email from openscienceframework-noreply to specified destination

    :param to: string destination address
    :param subject: subject of email
    :param message: body of message

    :return: True if successful
    """
    fro = "openscienceframework-noreply@openscienceframework.org"
    msg = MIMEText(message)
    msg['Subject'] = subject
    msg['From'] = fro 
    msg['To'] = to
    
    s = smtplib.SMTP('mail.openscienceframework.org')
    s.ehlo()
    s.starttls()
    s.ehlo()
    s.login('openscienceframework-noreply@openscienceframework.org', '5mYur3N6')
    s.sendmail('openscienceframework-noreply@openscienceframework.org', [to], msg.as_string())
    s.quit()
    return True

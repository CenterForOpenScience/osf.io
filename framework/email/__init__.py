import smtplib
from email.mime.text import MIMEText

def send_email(to=None, subject=None, message=None):
    # TODO Should be a Task
    fro="openscienceframework-noreply@openscienceframework.org"
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
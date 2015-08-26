import datetime

from modularodm import Q
from website.mails.mail_triggers import QueuedEmail

queued_emails = list(QueuedEmail.find(Q('send_at', 'lt', datetime.datetime.utcnow()) & Q('sent', 'eq', False)))
for email in queued_emails:
    email.send_email

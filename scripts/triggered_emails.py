from datetime import datetime, timedelta
from framework.transactions.context import TokuTransaction
from website.app import init_app
from modularodm import Q
from website.models import QueuedEmail, SentEmail
from framework.auth import User

def main():
    queued_emails = list(QueuedEmail.find(Q('send_at', 'lt', datetime.utcnow()) & Q('sent', 'eq', False)))

    for email in queued_emails:
        with TokuTransaction():
            email.send_email()

    inactive_users = list(User.find(Q('date_last_login', 'lt', datetime.utcnow() - timedelta(weeks=4))))
    inactive_emails = list(SentEmail.find(Q('email_type', 'eq', 'no_login')))
    users_sent = []
    for email in inactive_emails:
        users_sent.append(email.to_)
    for user in inactive_users:
        if user not in users_sent:
            email = QueuedEmail()
            email.create(to_user=user, email_type='no_login', send_at=datetime.utcnow())

if __name__ == '__main__':
    init_app(routes=False)
    main()

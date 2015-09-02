from datetime import datetime, timedelta
from framework.transactions.context import TokuTransaction
from website.app import init_app
from modularodm import Q
from website import mails
#from website.models import QueuedMail, SentQueuedMail
from framework.auth import User

def main():
    inactive_users = list(User.find(Q('date_last_login', 'lt', datetime.utcnow() - timedelta(weeks=4))))
    inactive_emails = list(mails.SentQueuedMail.find(Q('email_type', 'eq', 'no_login')))
    users_sent = []
    for email in inactive_emails:
        users_sent.append(email.to_)
    for user in inactive_users:
        if user not in users_sent:
            with TokuTransaction():
                mails.queue_mail(
                    to_addr=user.username,
                    mail=mails.NO_LOGIN,
                    send_at=datetime.utcnow(),
                    user=user
                )

    queued_emails = list(mails.QueuedMail.find(Q('send_at', 'lt', datetime.utcnow())))

    for mail in queued_emails:
        with TokuTransaction():
            mail.send_mail()

if __name__ == '__main__':
    init_app(routes=False)
    main()

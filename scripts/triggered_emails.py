from datetime import datetime, timedelta
from framework.transactions.context import TokuTransaction
from website.app import init_app
from modularodm import Q
from website import mails
from framework.auth import User

def main():
    inactive_users = list(User.find(Q('date_last_login', 'lt', datetime.utcnow() - timedelta(weeks=4))))
    inactive_emails = list(mails.QueuedMail.find(Q('email_type', 'eq', 'no_login')))
    users_sent = []
    for email in inactive_emails:
        users_sent.append(email.user)
    for user in set(inactive_users) - set(users_sent):
        with TokuTransaction():
            mails.queue_mail(
                to_addr=user.username,
                mail=mails.NO_LOGIN,
                send_at=datetime.utcnow(),
                user=user,
                fullname=user.fullname
            )
            print 'EMAIL QUEUED TO: ' + user.fullname

    #find all emails to be sent, pops the top one for each user(to obey the once
    #a week requirement), checks to see if one has been sent this week, and if
    #not send the email, otherwise leave it in the queue
    queued_emails = list(mails.QueuedMail.find(
        Q('send_at', 'lt', datetime.utcnow()) &
        Q('sent_at', 'eq', None)
    ))

    user_queue = {}
    for email in queued_emails:
        user_queue.setdefault(email.user._id, []).append(email)

    for user in user_queue.values():
        mail = user[0]
        mails_past_week = list(mails.QueuedMail.find(
            Q('user', 'eq', mail.user) &
            Q('sent_at', 'gt', datetime.utcnow() - timedelta(days=7))
        ))
        if not len(mails_past_week):
            with TokuTransaction():
                mail.send_mail()

if __name__ == '__main__':
    init_app(routes=False)
    main()

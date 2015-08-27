import datetime
from framework.transactions.context import TokuTransaction
from website.app import init_app
from modularodm import Q
from website.mails.mail_triggers import QueuedEmail

def main():
    queued_emails = list(QueuedEmail.find(Q('send_at', 'lt', datetime.datetime.utcnow()) & Q('sent', 'eq', False)))

    for email in queued_emails:
        with TokuTransaction():
            email.send_email()

if __name__ == '__main__':
    init_app(routes=False)
    main()

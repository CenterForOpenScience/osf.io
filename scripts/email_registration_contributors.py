"""Script for sending OSF emails to all users who contribute to registrations."""

from modularodm import Q

from website import models
from website.app import init_app
from website.mails import Mail, send_mail


def main():
    registrations = models.Node.find(Q('is_registration', 'eq', True))
    contributors = []
    for node in registrations:
        contributors.extend([contrib for contrib in node.contributors if contrib not in contributors])

    mailer = Mail('email_contributors_of_registrations', 'Important Update to Registrations on OSF')

    for contrib in contributors:
        send_mail(contrib.username, mailer, user=contrib)

if __name__ == '__main__':
    init_app(routes=False, mfr=False)
    main()

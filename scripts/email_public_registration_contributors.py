"""Script for sending OSF email to all users who contribute to public registrations."""

import datetime

from modularodm import Q

from website import models
from website.app import init_app
from website.mails import Mail, send_mail


def main():
    public_registrations = models.Node.find(Q('is_registration', 'eq', True) & Q('is_public', 'eq', True))
    contributors = []
    for node in public_registrations:
        contributors.extend([contrib for contrib in node.contributors if contrib not in contributors])

    # FIXME: need cutoff date from Brian or Sara
    cutoff_date = datetime.date.today() + datetime.timedelta(days=14)

    # FIXME: subject line needs to be revised by Brian or Sara
    mailer = Mail('email_contributors_of_public_registrations', 'SUBJECT LINE -- Sara and BrianN please advice')

    for contrib in contributors:
        send_mail(
            contrib.username,
            mailer,
            user=contrib,
            cutoff_date=cutoff_date
        )


if __name__ == '__main__':
    init_app(routes=False, mfr=False)
    main()
"""Script for sending OSF emails to all users who contribute to registrations."""

import datetime
import logging

from modularodm import Q

from website import models
from website.app import init_app
from website.mails import Mail, send_mail

from scripts import utils as script_utils


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

MESSAGE_NAME = 'retraction_and_embargo_addition'
MAILER = Mail(
    'email_contributors_of_registrations',
    'Important Update to Registrations on OSF'
)


def send_retraction_and_embargo_addition_message(contrib, label, mail, dry_run=True):
    if label in contrib.security_messages:
        return
    logger.info('Sending message to user {0!r}'.format(contrib))
    if not dry_run:
        send_mail(contrib.username, mail, user=contrib)
        contrib.security_messages[MESSAGE_NAME] = datetime.datetime.utcnow()
        contrib.save()


def get_registration_contributors():
    """Returns set of users that contribute to registrations."""
    registrations = models.Node.find(Q('is_registration', 'eq', True))
    contributors = []

    def has_received_message(contrib):
        query = (Q('_id', 'eq', contrib._id) & Q('security_messages.{0}'.format(MESSAGE_NAME), 'exists', False))
        return models.User.find(query).count() == 0

    for node in registrations:
        contributors.extend([contrib for contrib in node.contributors if contrib not in contributors and not has_received_message(contrib)])

    return contributors


def main(dry_run):
    contributors = get_registration_contributors()

    if not dry_run:
        logger.info('Emailing {0} users regarding upcoming registration changes'.format(len(contributors)))
    for contrib in contributors:
        send_retraction_and_embargo_addition_message(contrib, MESSAGE_NAME, MAILER, dry_run=dry_run)


if __name__ == '__main__':
    import sys
    dry_run = 'dry' in sys.argv
    if not dry_run:
        script_utils.add_file_logger(logger, __file__)
    init_app(routes=False, mfr=False)
    main(dry_run)

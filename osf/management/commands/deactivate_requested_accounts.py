import logging

from website import mails
from django.utils import timezone

from framework.celery_tasks import app as celery_app
from website.app import setup_django
setup_django()
from osf.models import OSFUser
from website.settings import OSF_SUPPORT_EMAIL, OSF_CONTACT_EMAIL
from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def deactivate_requested_accounts(dry_run=True):
    users = OSFUser.objects.filter(requested_deactivation=True, contacted_deactivation=False, date_disabled__isnull=True)

    for user in users:
        if user.has_resources:
            logger.info('OSF support is being emailed about deactivating the account of user {}.'.format(user._id))
            if not dry_run:
                mails.send_mail(
                    to_addr=OSF_SUPPORT_EMAIL,
                    mail=mails.REQUEST_DEACTIVATION,
                    user=user,
                    can_change_preferences=False,
                )
        else:
            logger.info('Disabling user {}.'.format(user._id))
            if not dry_run:
                user.disable_account()
                user.is_registered = False
                mails.send_mail(
                    to_addr=user.username,
                    mail=mails.REQUEST_DEACTIVATION_COMPLETE,
                    user=user,
                    contact_email=OSF_CONTACT_EMAIL,
                    can_change_preferences=False,
                )

        user.contacted_deactivation = True
        user.email_last_sent = timezone.now()
        if not dry_run:
            user.save()

    if dry_run:
        logger.info('Dry run complete')


@celery_app.task(name='management.commands.deactivate_requested_accounts')
def main(dry_run=False):
    """
    This task runs nightly and emails users who want to delete there account with info on how to do so. Users who don't
    have any content can be automatically deleted.
    """
    if dry_run:
        logger.info('This is a dry run; no changes will be saved, and no emails will be sent.')
    deactivate_requested_accounts(dry_run=dry_run)


class Command(BaseCommand):
    help = '''
    If there are any users who want to be deactivated we will either: immediately deactivate, or if they have active
    resources (undeleted nodes, preprints etc) we contact admin to guide the user through the deactivation process.
    '''

    def add_arguments(self, parser):
        super(Command, self).add_arguments(parser)
        parser.add_argument(
            '--dry',
            action='store_true',
            dest='dry_run',
            help='Dry run',
        )

    # Management command handler
    def handle(self, *args, **options):
        dry_run = options.get('dry_run', True)
        main(dry_run=dry_run)

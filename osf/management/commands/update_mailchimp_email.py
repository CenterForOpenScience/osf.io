import logging
import datetime

from django.core.management.base import BaseCommand
from osf.models import OSFUser
from website import mailchimp_utils

logger = logging.getLogger(__name__)


def update_mailchimp_email():
    users_updated = 0
    for user in OSFUser.objects.filter(deleted__isnull=True):
        for list_name, subscription in user.mailchimp_mailing_lists.items():
            if subscription:
                mailchimp_utils.subscribe_mailchimp(list_name, user._id)
        users_updated += 1

    return users_updated


class Command(BaseCommand):
    help = '''Backfills users that might have updated their email and not had it updated in mailchimp'''

    def handle(self, *args, **options):
        script_start_time = datetime.datetime.now()
        logger.info(f'Script started time: {script_start_time}')

        users_updated = update_mailchimp_email()

        script_finish_time = datetime.datetime.now()
        logger.info(f'Script finished time: {script_finish_time}')
        script_runtime = script_finish_time - script_start_time
        logger.info(f'Run time {script_runtime}')
        logger.info(f'{users_updated} Users updated in mailchimp')

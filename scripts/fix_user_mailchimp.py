import logging
import sys
from datetime import datetime

from django.db import transaction
from django.utils import timezone

from website.app import setup_django
setup_django()
from osf.models import OSFUser
from scripts import utils as script_utils
from website.mailchimp_utils import subscribe_mailchimp
from website import settings

logger = logging.getLogger(__name__)


def main():
    dry = '--dry' in sys.argv
    if not dry:
        # If we're not running in dry mode log everything to a file
        script_utils.add_file_logger(logger, __file__)

    with transaction.atomic():
        start_time = datetime.strptime('2017-12-20 08:25:25', '%Y-%m-%d %H:%M:%S')
        start_time = start_time.replace(tzinfo=timezone.now().tzinfo)

        end_time = datetime.strptime('2017-12-20 18:05:00', '%Y-%m-%d %H:%M:%S')
        end_time = end_time.replace(tzinfo=timezone.now().tzinfo)

        users = OSFUser.objects.filter(is_registered=True, date_disabled__isnull=True, date_registered__range=[start_time, end_time])

        if not dry:
            count = 0
            for user in users:
                if not user.mailchimp_mailing_lists[settings.MAILCHIMP_GENERAL_LIST]:
                    subscribe_mailchimp(settings.MAILCHIMP_GENERAL_LIST, user._id)
                    logger.info('User {} has been subscribed to OSF general mailing list'.format(user._id))
                    count += 1

            logger.info('{} users have been subscribed to OSF general mailing list'.format(count))

        if dry:
            raise Exception('Abort Transaction - Dry Run')
    print('Done')

if __name__ == '__main__':
    main()

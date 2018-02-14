import logging
import pytz
import sys
from datetime import datetime

from django.db import transaction

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
        start_time = datetime(2017, 12, 20, 8, 25, 25, tzinfo=pytz.UTC)
        end_time = datetime(2017, 12, 20, 18, 5, 1, tzinfo=pytz.UTC)

        users = OSFUser.objects.filter(is_registered=True, date_disabled__isnull=True, date_registered__range=[start_time, end_time])

        count = 0
        for user in users:
            if settings.MAILCHIMP_GENERAL_LIST not in user.mailchimp_mailing_lists:
                if not dry:
                    subscribe_mailchimp(settings.MAILCHIMP_GENERAL_LIST, user._id)
                    logger.info('User {} has been subscribed to OSF general mailing list'.format(user._id))
                count += 1

        logger.info('{} users have been subscribed to OSF general mailing list'.format(count))

        if dry:
            raise Exception('Abort Transaction - Dry Run')
    print('Done')

if __name__ == '__main__':
    main()

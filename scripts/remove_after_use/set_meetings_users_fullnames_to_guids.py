import sys
import logging

from website.app import setup_django
setup_django()

from osf.models import OSFUser
from scripts import utils as script_utils

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def main():
    dry_run = '--dry' in sys.argv
    if not dry_run:
        script_utils.add_file_logger(logger, __file__)
    users = OSFUser.objects.filter(fullname__regex=r'^[A-Za-z0-9\.\+_-]+@[A-Za-z0-9\._-]+\.[a-zA-Z]*$', tags__name='osf4m')
    count = users.count()
    logger.info('{} users found added by OSF 4 Meetings with emails for fullnames'.format(count))
    for user in users:
        logger.info('Changing OSFUser {} fullname from {} to {}'.format(user._id, user.fullname, user._id))
        user.fullname = user._id
        if not dry_run:
            user.save()
    logger.info('Finished migrating {} users'.format(count))


if __name__ == '__main__':
    main()

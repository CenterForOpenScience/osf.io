import sys
import logging
import datetime

from website import models
from website.app import init_app

logger = logging.getLogger(__name__)


def main():
    init_app(routes=False)
    dry_run = 'dry' in sys.argv
    logger.warn('All active users will have their date_last_login update to now')
    if dry_run:
        logger.warn('Dry_run mode')
    for user in models.User.find():
        logger.info('User {0} "date_last_login" updated'.format(user.username))
        if not dry_run and user.is_active:
            user.date_last_login = datetime.datetime.utcnow()
            user.save()

if __name__ == '__main__':
    main()

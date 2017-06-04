"""
used to update all users date_last_login the time the script is run, as date_last_login was not being updated.
This will allow proper use of no_login email starting 2 months from day migration is run for old users.
"""
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
        if user.is_active:
            logger.info('User {0} "date_last_login" updated'.format(user._id))
            if not dry_run:
                user.date_last_login = datetime.datetime.utcnow()
                user.save()

if __name__ == '__main__':
    main()

"""
Clears the `chronos_user_id` field on all OSFUser instances. Needed for switching from one Chronos server to another.
"""
import sys
import logging
import django
django.setup()

from osf import models
from website.app import init_app

logger = logging.getLogger(__name__)

def main(dry_run=True):
    if dry_run:
        for user in models.OSFUser.objects.filter(chronos_user_id__isnull=False):
            logger.info('Reset chronos_user_id for user with guid {}'.format(user._id))
        for submission in models.ChronosSubmission.objects.all():
            logger.info('Deleting chronos submission with id {}'.format(submission.publication_id))
    else:
        models.OSFUser.objects.all().update(chronos_user_id=None)
        models.ChronosSubmission.objects.all().delete()
        logger.info('Finished resetting all OSFUser chronos_user_id')
        logger.info('Finished deleting all ChronosSubmission instances')


if __name__ == '__main__':
    init_app(routes=False)
    dry = '--dry' in sys.argv
    main(dry_run=dry)

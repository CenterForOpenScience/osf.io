import logging
import sys
import django
from django.db import transaction
django.setup()

from osf.models import Registration
from scripts import utils as script_utils
from website import settings
from website.app import init_app
from website.project.tasks import on_registration_updated

logger = logging.getLogger(__name__)

def migrate():
    assert settings.SHARE_URL, 'SHARE_URL must be set to migrate.'
    assert settings.SHARE_API_TOKEN, 'SHARE_API_TOKEN must be set to migrate.'
    registrations = Registration.objects.all()
    registrations_count = len(registrations)
    successes = []
    failures = []
    count = 0

    logger.info('Preparing to migrate {} registrations.'.format(registrations_count))
    for registration in registrations:
        if not registration.is_public or registration.is_deleted:
            pass
        count += 1
        logger.info('{}/{} - {}'.format(count, registrations_count, registration._id))
        try:
            on_registration_updated(registration)
        except Exception as e:
            # TODO: This reliably fails for certain nodes with
            # IncompleteRead(0 bytes read)
            failures.append(registration._id)
            logger.warn('Encountered exception {} while posting to SHARE for registration {}'.format(e, registration._id))
        else:
            successes.append(registration._id)

    logger.info('Successes: {}'.format(successes))
    logger.info('Failures: {}'.format(failures))


def main():
    dry_run = '--dry' in sys.argv
    if not dry_run:
        script_utils.add_file_logger(logger, __file__)
    init_app(set_backends=True, routes=False)
    with transaction.atomic():
        migrate()
        if dry_run:
            transaction.rollback()

if __name__ == '__main__':
    main()

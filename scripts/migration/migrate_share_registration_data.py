# TODO: Consider rewriting as management command
import logging
import sys
import django
from django.db import transaction
django.setup()

from osf.models import Registration
from scripts import utils as script_utils
from website import settings
from website.app import init_app
from api.share.utils import update_share

logger = logging.getLogger(__name__)


def migrate(dry_run):
    assert settings.SHARE_URL, 'SHARE_URL must be set to migrate.'
    assert settings.SHARE_API_TOKEN, 'SHARE_API_TOKEN must be set to migrate.'
    registrations = Registration.objects.filter(is_deleted=False, is_public=True)
    registrations_count = registrations.count()
    count = 0

    logger.info(f'Preparing to migrate {registrations_count} registrations.')
    for registration in registrations.iterator():
        count += 1
        logger.info(f'{count}/{registrations_count} - {registration._id}')
        if not dry_run:
            update_share(registration)
        logger.info(f'Registration {registration._id} was sent to SHARE.')


def main():
    dry_run = '--dry' in sys.argv
    if not dry_run:
        script_utils.add_file_logger(logger, __file__)
    init_app(set_backends=True, routes=False)
    with transaction.atomic():
        migrate(dry_run)

if __name__ == '__main__':
    main()

# TODO: Consider rewriting as management command
import logging
import sys
import time

from scripts import utils as script_utils
from website.app import setup_django
from django.apps import apps
from website.preprints.tasks import on_preprint_updated
from website import settings

logger = logging.getLogger(__name__)


def get_targets():
    Preprint = apps.get_model('osf.Preprint')
    return Preprint.objects.filter().values_list('guids___id', flat=True)

def migrate(dry=True):
    assert settings.SHARE_URL, 'SHARE_URL must be set to migrate.'
    assert settings.SHARE_API_TOKEN, 'SHARE_API_TOKEN must be set to migrate.'
    targets = get_targets()
    target_count = len(targets)
    successes = []
    failures = []
    count = 0

    logger.info('Preparing to migrate {} preprints.'.format(target_count))
    for preprint_id in targets:
        count += 1
        logger.info('{}/{} - {}'.format(count, target_count, preprint_id))
        try:
            if not dry:
                on_preprint_updated(preprint_id, update_share=True)
                # Sleep in order to be nice to EZID
                time.sleep(1)
        except Exception as e:
            # TODO: This reliably fails for certain nodes with
            # IncompleteRead(0 bytes read)
            failures.append(preprint_id)
            logger.warn('Encountered exception {} while posting to SHARE for preprint {}'.format(e, preprint_id))
        else:
            successes.append(preprint_id)

    logger.info('Successes: {}'.format(successes))
    logger.info('Failures: {}'.format(failures))


def main():
    dry_run = '--dry' in sys.argv
    if not dry_run:
        script_utils.add_file_logger(logger, __file__)
    setup_django()
    migrate(dry=dry_run)

if __name__ == '__main__':
    main()

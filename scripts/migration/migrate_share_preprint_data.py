import logging
import sys

from framework.mongo import database
from framework.transactions.context import TokuTransaction
from scripts import utils as script_utils
from website.app import init_app
from website.models import PreprintService
from website.preprints.tasks import on_preprint_updated
from website import settings

logger = logging.getLogger(__name__)


def get_targets():
    return [p['_id'] for p in database['preprintservice'].find()]

def migrate():
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
            on_preprint_updated(preprint_id)
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
    init_app(set_backends=True, routes=False)
    with TokuTransaction():
        migrate()
        if dry_run:
            raise RuntimeError('Dry run, transaction rolled back.')

if __name__ == "__main__":
    main()

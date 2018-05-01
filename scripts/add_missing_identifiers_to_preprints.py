# -*- coding: utf-8 -*-
import sys
import time
import logging
import django
from scripts import utils as script_utils
from django.db import transaction

from framework.celery_tasks import app as celery_app

from website.app import init_app
from website.identifiers.utils import request_identifiers, parse_identifiers

django.setup()
logger = logging.getLogger(__name__)


def add_identifiers_to_preprints(dry_run=True):
    from osf.models import PreprintService

    preprints_without_identifiers = PreprintService.objects.filter(is_published=True, preprint_doi_created__isnull=True)
    logger.info('About to add identifiers to {} preprints.'.format(preprints_without_identifiers.count()))
    identifiers_added = 0

    for preprint in preprints_without_identifiers:
        logger.info('Saving identifier for preprint {} from source {}'.format(preprint._id, preprint.provider.name))

        if not dry_run:
            doi_client_response = request_identifiers(preprint)
            id_dict = parse_identifiers(doi_client_response)
            preprint.set_identifier_values(doi=id_dict['doi'])
            preprint.save()

            doi = preprint.get_identifier('doi')
            assert preprint._id.upper() in doi.value
            identifiers_added += 1

            logger.info('Created DOI {} for Preprint with guid {} from service {}'.format(doi.value, preprint._id, preprint.provider.name))
            time.sleep(1)
        else:
            logger.info('Dry run - would have created identifier for preprint {} from service {}'.format(preprint._id, preprint.provider.name))

    logger.info('Finished Adding identifiers to {} preprints.'.format(identifiers_added))


def main(dry_run=True):
    add_identifiers_to_preprints(dry_run)
    if dry_run:
        # When running in dry_run mode force the transaction to rollback
        raise Exception('Dry Run complete -- not actually saved')

@celery_app.task(name='scripts.add_missing_identifiers_to_preprints')
def run_main(dry_run=True):
    init_app(routes=False)
    if not dry_run:
        # If we're not running in dry mode log everything to a file
        script_utils.add_file_logger(logger, __file__)

    # Finally run the migration
    with transaction.atomic():
        main(dry_run=dry_run)

if __name__ == "__main__":
    dry_run = '--dry' in sys.argv
    run_main(dry_run=dry_run)

import sys
import time
import logging
from scripts import utils as script_utils

from website.app import setup_django
from website.identifiers.utils import request_identifiers_from_ezid, parse_identifiers

setup_django()
logger = logging.getLogger(__name__)


def main(dry=True):
    from osf.models import PreprintService

    preprints_without_identifiers = PreprintService.objects.filter(identifiers__isnull=True, is_published=True, node__is_deleted=False)
    logger.info('About to add identifiers to {} preprints.'.format(preprints_without_identifiers.count()))

    for preprint in preprints_without_identifiers:
        logger.info('Saving identifier for preprint {} from source {}'.format(preprint._id, preprint.provider.name))

        if not dry:
            ezid_response = request_identifiers_from_ezid(preprint)
            id_dict = parse_identifiers(ezid_response)
            preprint.set_identifier_values(doi=id_dict['doi'], ark=id_dict['ark'])
            preprint.save()

            doi = preprint.get_identifier('doi')
            assert preprint._id.upper() in doi.value

            logger.info('Created DOI {} for Preprint with guid {} from service {}'.format(doi.value, preprint._id, preprint.provider.name))
            time.sleep(1)
        else:
            logger.info('Dry run - would have created identifier for preprint {} from service {}'.format(preprint._id, preprint.provider.name))

    logger.info('Finished Adding identifiers to {} preprints.'.format(preprints_without_identifiers.count()))


if __name__ == '__main__':
    dry = '--dry' in sys.argv
    if not dry:
        # If we're not running in dry mode log everything to a file
        script_utils.add_file_logger(logger, __file__)

    # Allow setting the log level just by appending the level to the command
    if '--debug' in sys.argv:
        logger.setLevel(logging.DEBUG)
    elif '--warning' in sys.argv:
        logger.setLevel(logging.WARNING)
    elif '--info' in sys.argv:
        logger.setLevel(logging.INFO)
    elif '--error' in sys.argv:
        logger.setLevel(logging.ERROR)

    # Finally run the migration
    main(dry=dry)

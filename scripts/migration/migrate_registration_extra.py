"""
Changes existing question.extra on a draft to a list
required for multiple files attached to a question
"""
import sys
import logging

from modularodm import Q
from website.app import init_app
from scripts import utils as scripts_utils
from website.models import DraftRegistration
from website.prereg.utils import get_prereg_schema
from framework.transactions.context import TokuTransaction


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def migrate_drafts(dry):

    PREREG_CHALLENGE_METASCHEMA = get_prereg_schema()
    draft_registrations = DraftRegistration.find(
        Q('registration_schema', 'eq', PREREG_CHALLENGE_METASCHEMA) &
        Q('approval', 'eq', None) &
        Q('registered_node', 'eq', None)
    )
    count = 0
    for r in draft_registrations:
        data = r.registration_metadata
        for q, ans in data.iteritems():
            files = ans['extra']
            if type(files) is dict:
                if len(files.keys()) == 0:
                    ans['extra'] = []
                else:
                    ans['extra'] = [files]
                    count += 1
        if not dry:
            r.save()
    logger.info('Done with {0} drafts migrated.'.format(count))


def main(dry=True):
    init_app(set_backends=True, routes=False)
    scripts_utils.add_file_logger(logger, __file__)
    migrate_drafts(dry)



if __name__ == '__main__':
    dry_run = 'dry' in sys.argv
    with TokuTransaction():
        main(dry=dry_run)
        if dry_run:
            raise RuntimeError('Dry run, rolling back transaction.')

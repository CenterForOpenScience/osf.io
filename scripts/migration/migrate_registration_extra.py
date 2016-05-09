"""
Changes existing question.extra on Prereg registrations
to a list. Required for multiple files attached to a question
"""
import sys
import logging

from modularodm import Q
from website.app import init_app
from scripts import utils as scripts_utils
from website.models import Node
from website.prereg.utils import get_prereg_schema
from framework.transactions.context import TokuTransaction


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def migrate_file_meta(question):
    files = question.get('extra')
    if isinstance(files, dict):
        if len(files) == 0:
            question['extra'] = []
        else:
            question['extra'] = [files]
        return True
    return False


def migrate():
    PREREG_CHALLENGE_METASCHEMA = get_prereg_schema()
    registrations = Node.find(
        Q('is_registration', 'eq', True) &
        Q('registered_schema', 'eq', PREREG_CHALLENGE_METASCHEMA)
    )
    count = 0
    for reg in registrations:
        data = reg.registered_meta[PREREG_CHALLENGE_METASCHEMA._id]
        migrated = False
        for question in data.values():
            if isinstance(question.get('value'), dict):
                for value in question['value'].values():
                    migrated = migrate_file_meta(value)
            else:
                migrated = migrate_file_meta(question)
        reg.save()
        if migrated:
            count += 1
    logger.info('Done with {0} preregistrations migrated.'.format(count))

if __name__ == '__main__':
    dry_run = 'dry' in sys.argv
    if not dry_run:
        scripts_utils.add_file_logger(logger, __file__)
    with TokuTransaction():
        init_app(set_backends=True, routes=False)
        migrate()
        if dry_run:
            raise RuntimeError('Dry run, rolling back transaction.')

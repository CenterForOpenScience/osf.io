"""
Changes existing question.extra on Prereg registrations
to a list. Required for multiple files attached to a question
"""
import sys
import logging

from modularodm import Q
from website.app import init_app
from scripts import utils as scripts_utils
from website.models import Node, DraftRegistration
from website.prereg.utils import get_prereg_schema
from framework.transactions.context import TokuTransaction


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def migrate_file_meta(question):
    files = question.get('extra')
    migrated = False
    if files == [{}]:
        question['extra'] = []
        migrated = True
    return migrated

def migrate_registrations():
    PREREG_CHALLENGE_METASCHEMA = get_prereg_schema()
    registrations = Node.find(
        Q('is_registration', 'eq', True) &
        Q('registered_schema', 'eq', PREREG_CHALLENGE_METASCHEMA)
    )
    count = 0
    for reg in registrations:
        data = reg.registered_meta[PREREG_CHALLENGE_METASCHEMA._id]
        migrated = False
        logger.debug('Reading preregistration with id: {0}'.format(reg._id))
        for question in data.values():
            if isinstance(question.get('value'), dict):
                for value in question['value'].values():
                    migrated_one = migrate_file_meta(value)
                    if migrated_one and not migrated:
                        migrated = True
            else:
                migrated_one = migrate_file_meta(question)
                if migrated_one and not migrated:
                    migrated = True
        if migrated:
            reg.save()
            count += 1
            logger.info('Migrated preregistration with id: {0}'.format(reg._id))
    logger.info('Done with {0} prereg registrations migrated.'.format(count))


def migrate_drafts():
    PREREG_CHALLENGE_METASCHEMA = get_prereg_schema()
    draft_registrations = DraftRegistration.find(
        Q('registration_schema', 'eq', PREREG_CHALLENGE_METASCHEMA)
    )
    count = 0
    for draft in draft_registrations:
        migrated = False
        logger.debug('Reading preregistration draft with id: {0}'.format(draft._id))
        for answer in draft.registration_metadata.values():
            if isinstance(answer.get('value'), dict):
                for value in answer['value'].values():
                    migrated_one = migrate_file_meta(value)
                    if migrated_one and not migrated:
                        migrated = True
            else:
                migrated_one = migrate_file_meta(answer)
                if migrated_one and not migrated:
                    migrated = True
        if migrated:
            draft.save()
            count += 1
            logger.info('Migrated preregistration draft {0}'.format(draft._id))
    logger.info('Done with {0} prereg drafts migrated.'.format(count))


def migrate():
    migrate_registrations()
    migrate_drafts()


if __name__ == '__main__':
    dry_run = '--dry' in sys.argv
    if not dry_run:
        scripts_utils.add_file_logger(logger, __file__)
    with TokuTransaction():
        init_app(set_backends=True, routes=False)
        migrate()
        if dry_run:
            raise RuntimeError('Dry run, rolling back transaction.')

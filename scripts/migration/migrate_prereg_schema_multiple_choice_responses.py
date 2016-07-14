"""
Small migration - Prereg challenge schema q5 mult choice responses have extra trailing space.  This gets confusing when
user trying to update prereg draft via API.
"""

import sys
import logging

from modularodm import Q
from website.app import init_app
from scripts import utils as scripts_utils
from website.models import DraftRegistration, Node, MetaSchema
from framework.transactions.context import TokuTransaction


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def migrate_drafts_q5_metadata(schema):
    """
    Finds Prereg Challenge draft registrations and corrects q5 response metadata
    """
    drafts = DraftRegistration.find(Q('registration_schema', 'eq', schema))
    total_drafts = drafts.count()
    logger.info('Examining {} drafts for q5 metadata'.format(total_drafts))
    draft_count = 0
    for draft in drafts:
        draft_count += 1
        if draft.registration_metadata.get('q5', {}).get('value', {}):
            draft.registration_metadata['q5']['value'] = draft.registration_metadata['q5']['value'].rstrip()
            draft.save()
            logger.info('{}/{} Migrated q5 response for {}'.format(draft_count, total_drafts, draft._id))
        else:
            logger.info('{}/{} q5 not answered. No change needed for {}.'.format(draft_count, drafts.count(), draft._id))

def migrate_registrations_q5_metadata(schema):
    """
    Finds Prereg Challenge registrations whose registered_meta includes q5 and corrects
    """
    registrations = Node.find(Q('is_registration', 'eq', True) & Q('registered_schema', 'eq', schema))
    total_reg = registrations.count()
    logger.info('Examining {} registrations for q5 metadata'.format(total_reg))
    reg_count = 0

    for reg in registrations:
        reg_count += 1
        if reg.registered_meta.get(schema._id, {}).get('q5', {}).get('value', {}):
            reg.registered_meta[schema._id]['q5']['value'] = reg.registered_meta[schema._id]['q5']['value'].rstrip()
            reg.save()
            logger.info('{}/{} Migrated q5 response for {}'.format(reg_count, total_reg, reg._id))
        else:
            # q5 is a required question, so should be answered, but just in case...
            logger.info('{}/{} q5 not answered. No change needed for {}.'.format(reg_count, total_reg, reg._id))

def main(dry=True):
    init_app(set_backends=True, routes=False)
    if not dry:
        scripts_utils.add_file_logger(logger, __file__)
    prereg = MetaSchema.find_one(
            Q('name', 'eq', "Prereg Challenge"))
    migrate_drafts_q5_metadata(prereg)
    migrate_registrations_q5_metadata(prereg)


if __name__ == '__main__':
    dry_run = '--dry' in sys.argv
    with TokuTransaction():
        main(dry=dry_run)
        if dry_run:
            raise RuntimeError('Dry run, rolling back transaction.')

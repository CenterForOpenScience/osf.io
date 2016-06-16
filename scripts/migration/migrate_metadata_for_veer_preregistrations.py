"""
Small migration - "Pre-Registration in Social Psychology (van 't Veer & Giner-Sorolla, 2016): Pre-Registration" schema is missing a key.
Modifies registration_metadata in drafts and registrations that will have an undefined key.
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

def migrate_drafts_metadata_key(schema):
    """
    Finds Veer draft registrations whose registration_metadata has an undefined key and corrects.
    """
    drafts = DraftRegistration.find(Q('registration_schema', 'eq', schema))
    total_drafts = drafts.count()
    logger.info('Examining {} drafts for improper key'.format(total_drafts))
    draft_count = 0
    for draft in drafts:
        draft_count += 1
        if draft.registration_metadata.get('recommended-methods', {}).get('value', {}).get('undefined', {}):
            draft.registration_metadata['recommended-methods']['value']['procedure'] = draft.registration_metadata['recommended-methods']['value'].pop('undefined')
            draft.save()
            logger.info('{}/{} Migrated key for {}'.format(draft_count, total_drafts, draft._id))
        else:
            logger.info('{}/{} Key already correct for {}. No change.'.format(draft_count, drafts.count(), draft._id))

def migrate_registrations_metadata_key(schema):
    """
    Finds Veer registrations whose registered_meta has an undefined key and corrects.
    """
    registrations = Node.find(Q('is_registration', 'eq', True) & Q('registered_schema', 'eq', schema))
    total_reg = registrations.count()
    logger.info('Examining {} registrations for improper key'.format(total_reg))
    reg_count = 0

    for reg in registrations:
        reg_count += 1
        if reg.registered_meta.get(schema._id, {}).get('recommended-methods', {}).get('value', {}).get('undefined', {}):
            reg.registered_meta[schema._id]['recommended-methods']['value']['procedure'] = \
            reg.registered_meta[schema._id]['recommended-methods']['value'].pop('undefined')
            reg.save()
            logger.info('{}/{} Migrated key for {}'.format(reg_count, total_reg, reg._id))
        else:
            logger.info('{}/{} Key already correct for {}. No change.'.format(reg_count, total_reg, reg._id))

def main(dry=True):
    init_app(set_backends=True, routes=False)
    if not dry:
        scripts_utils.add_file_logger(logger, __file__)
    veer = MetaSchema.find_one(
            Q('name', 'eq',
              "Pre-Registration in Social Psychology (van 't Veer & Giner-Sorolla, 2016): Pre-Registration"))
    migrate_drafts_metadata_key(veer)
    migrate_registrations_metadata_key(veer)


if __name__ == '__main__':
    dry_run = '--dry' in sys.argv
    with TokuTransaction():
        main(dry=dry_run)
        if dry_run:
            raise RuntimeError('Dry run, rolling back transaction.')
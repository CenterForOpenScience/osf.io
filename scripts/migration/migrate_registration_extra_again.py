"""
Changes existing question.extra on all registrations and draft registrations
to a list. Required for multiple files attached to a question.
"""
import sys
import logging

from modularodm import Q
from website.app import init_app
from scripts import utils as scripts_utils
from website.models import Node, DraftRegistration
from framework.transactions.context import TokuTransaction

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def migrate_extras(queryset, dry=True):
    migrated = []
    errored = set()
    model_name = 'Node'
    for obj in queryset:
        # 1 transaction per obj, to prevent locking errors
        with TokuTransaction():
            changed = False
            if isinstance(obj, DraftRegistration):
                meta = [obj.registration_metadata]
                model_name = 'DraftRegistration'
                if obj.registered_node:  # Skip over drafts that have been completed
                    continue
            else:
                meta = obj.registered_meta.values()
                model_name = 'Node'
            if not meta:
                continue
            for data in meta:
                for question, answer in data.items():
                    if isinstance(answer.get('extra'), dict):
                        if not answer.get('extra'):
                            logger.info('Migrating extra for question {!r} on {} {}'.format(question, model_name, obj._id))
                            answer['extra'] = []
                            changed = True
                        else:  # We don't expect to get here
                            logger.error('Found non-empty "extra" on {} {} for question {!r}'.format(model_name, obj._id, question))
                            errored.add(obj)
                    for value in answer.values():
                        if isinstance(value, dict):
                            for k, v in value.items():
                                if isinstance(v, dict) and isinstance(v.get('extra'), dict):
                                    if not v.get('extra'):
                                        logger.info('Migrating {}/extra for question {} on {} {}'.format(k, question, model_name, obj._id))
                                        v['extra'] = []
                                        changed = True
                                    else:  # We don't expect to get here
                                        logger.error('Found non-empty "{}/extra" on {} {} for question {}'.format(k, model_name, obj._id, question))
                                        errored.add(obj)
            if changed:
                migrated.append(obj._id)
                if model_name == 'DraftRegistration':
                    # Prevent datetime_updated from being updated on save
                    obj._fields['datetime_updated']._auto_now = False
                if not dry:
                    changed = obj.save()
                    if model_name == 'DraftRegistration':
                        assert changed == {'registration_metadata'}, 'Expected only registration_metadata to change. Got: {}'.format(changed)
    return migrated, errored


def migrate(dry=True):
    registrations = Node.find(
        Q('is_registration', 'eq', True) &
        Q('registered_meta', 'ne', None)
    )
    regs_migrated, reg_errored = migrate_extras(registrations, dry=dry)

    drafts = DraftRegistration.find(Q('registration_metadata', 'ne', {}))
    drafts_migrated, drafts_errored = migrate_extras(drafts, dry=dry)

    logger.info('Migrated registered_meta for {} registrations'.format(len(regs_migrated)))
    if reg_errored:
        logger.error('{} errored: {}'.format(len(reg_errored), reg_errored))

    logger.info('Migrated registered_meta for {} draft registrations'.format(len(drafts_migrated)))
    if drafts_errored:
        logger.error('{} errored: {}'.format(len(drafts_errored), drafts_errored))



if __name__ == '__main__':
    dry_run = '--dry' in sys.argv
    if not dry_run:
        scripts_utils.add_file_logger(logger, __file__)
    init_app(set_backends=True, routes=False)
    migrate(dry=dry_run)

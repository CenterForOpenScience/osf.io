# -*- coding: utf-8 -*-
"""
Migrates Preregistration drafts with invalid uploader data.
Only migrates unapproved drafts. This will unselect files on questions that have the invalid data.
"""
import sys
import logging
from modularodm import Q
from copy import deepcopy

from framework.transactions.context import TokuTransaction

from website.app import init_app
from website.models import (
    DraftRegistration,
)
from website.prereg.utils import get_prereg_schema

from scripts import utils as script_utils


logger = logging.getLogger(__name__)


def migrate_draft_metadata(draft, test=False):
    changed = False
    for question in get_prereg_questions():
        qid = question['qid']
        metadata_value = deepcopy(draft.registration_metadata.get(qid, {}))
        if 'properties' in question:
            value = metadata_value.get('value')
            if not value:
                continue  # no response
            for prop in question['properties']:
                new_value = deepcopy(value)
                if prop['type'] == 'osf-upload':
                    try:
                        uid, uploader = [(k, v) for k, v in value.items() if 'uploader' in k][0]
                    except IndexError:
                        pass  # TODO
                    extra = uploader.get('extra')
                    if extra:
                        valid = [each for each in extra if 'data' in each]
                        if valid != extra:
                            logger.info(
                                'Draft {draft_id} on node {node_id} has invalid selected file data on question {qid}'
                                .format(draft_id=draft._id, node_id=draft.branched_from._id, qid=qid)
                            )
                            logger.info('Old value: {}'.format(value))

                            new_value[uid]['value'] = None  # unselect file
                            new_value[uid]['extra'] = valid  # clear invalid entries

                            logger.info('New value: {}'.format(new_value))
                            draft.update_metadata({qid: new_value})
                            draft.save()
                            changed = True
    return changed


def get_prereg_questions(prereg_schema=None):
    prereg_schema = prereg_schema or get_prereg_schema()
    prereg_questions = ()
    for page in prereg_schema.schema['pages']:
        prereg_questions = prereg_questions + tuple(page['questions'])
    return prereg_questions


def main(dry_run=False, test=False):
    init_app(set_backends=True, routes=False)
    prereg_schema = get_prereg_schema()
    count = 0
    with TokuTransaction():
        prereg_drafts = DraftRegistration.find(
            Q('registration_schema', 'eq', prereg_schema)
        )
        for draft in prereg_drafts:
            # only migrate unapproved drafts
            if draft.is_approved:
                continue
            changed = migrate_draft_metadata(draft, test)
            if changed:
                count += 1
        logger.info('Migrated {} drafts'.format(count))
        if dry_run:
            raise RuntimeError('Dry run, rolling back transaction')

if __name__ == '__main__':
    dry = '--dry' in sys.argv
    if not dry:
        script_utils.add_file_logger(logger, __file__)
    test = 'test' in sys.argv
    main(dry, test)

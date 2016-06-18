"""
a script to migrate draft registration metadata on Prereg Challenge submissions. The structure of some schema items
has changed to include optional file uploads, and existing file upload values need to be updated.
"""
import sys
import logging
from modularodm import Q
from modularodm.exceptions import NoResultsFound
import re
from copy import deepcopy

from framework.transactions.context import TokuTransaction

from website.app import init_app
from website.models import (
    MetaSchema,
    DraftRegistration,
    Node
)
from website.files.models import osfstorage

from scripts import utils as script_utils

init_app(set_backends=True, routes=False)

logger = logging.getLogger(__name__)

PREREG_SCHEMA = MetaSchema.find_one(
    Q('name', 'eq', 'Prereg Challenge') &
    Q('schema_version', 'eq', 2)
)
PREREG_QUESTIONS = ()
for page in PREREG_SCHEMA.schema['pages']:
    PREREG_QUESTIONS = PREREG_QUESTIONS + tuple(page['questions'])

def get_file_sha256(node_id, path):
    node = Node.load(node_id)

    try:
        file_node = osfstorage.OsfStorageFileNode.get(path, node)
    except NoResultsFound:
        raise RuntimeError("Couldn't find OsfStorageFile on node {0} with path {1}. Maybe it was moved or deleted?".format(node_id, path))
    latest_version = file_node.get_version()
    return latest_version.metadata.get('sha256')

def parse_view_url(view_url):
    match = re.search(
        r'/project/(?P<node_id>\w+)/files/osfstorage/(?P<path>\w+)/?$',
        view_url
    )
    if not match:
        raise RuntimeError('Invalid view URL: {0}'.format(view_url))
    else:
        items = match.groupdict()
        return items['node_id'], items['path']

def migrate_draft_metadata(draft, test=False):
    for question in PREREG_QUESTIONS:
        orig_data = None
        if test:
            orig_data = deepcopy(draft.registration_metadata)

        qid = question['qid']
        qtype = question['type']
        metadata_value = deepcopy(draft.registration_metadata.get(qid, {}))
        if qtype == 'osf-upload':
            if not metadata_value.get('value'):
                continue  # no file selected
            extra = metadata_value.get('extra')
            if extra:
                if not extra.get('viewUrl'):
                    continue
                node_id, path = parse_view_url(extra.get('viewUrl', ''))
                sha256 = get_file_sha256(node_id, path)
                file_name = extra.get('selectedFileName')
                old_value = deepcopy(draft.registration_metadata[qid])
                old_value['extra'] = {
                    'sha256': sha256,
                    'selectedFileName': file_name,
                    'nodeId': node_id,
                    'viewUrl': old_value['extra']['viewUrl']
                }
                draft.update_metadata(
                    {
                        qid: old_value
                    }
                )
            else:
                pass  # no metadata, skipping
        elif 'properties' in question:
            value = metadata_value.get('value')
            if not value:
                continue  # no response
            if not isinstance(value, dict):  # uploader added to question
                metadata_value['value'] = {
                    'question': {
                        'value': metadata_value['value']
                    }
                }
                draft.update_metadata({
                    qid: metadata_value
                })
                continue
            for prop in question['properties']:
                old_value = deepcopy(draft.registration_metadata[qid])
                if prop['type'] == 'osf-upload':
                    try:
                        uid, uploader = [(k, v) for k, v in value.items() if 'uploader' in k][0]
                    except IndexError:
                        pass  # TODO
                    extra = uploader.get('extra')
                    if not extra:
                        del old_value['value'][uid]
                        old_value['value']['uploader'] = {}
                    else:
                        if not extra.get('viewUrl'):
                            continue
                        node_id, path = parse_view_url(extra.get('viewUrl', ''))
                        sha256 = get_file_sha256(node_id, path)
                        file_name = extra.get('selectedFileName')
                        old_value['value']['uploader'] = old_value['value'][uid]
                        del old_value['value'][uid]
                        old_value['value']['uploader']['extra'].update({
                            'sha256': sha256,
                            'selectedFileName': file_name,
                            'nodeId': node_id
                        })
                else:
                    value = metadata_value.get('value', {})
                    # we can assume all prereg sumbissions have at most 2 properties
                    sqid, question = [(k, v) for k, v in value.items() if 'uploader' not in k][0]
                    if not sqid == 'question':
                        old_value['value']['question'] = question
                        del old_value['value'][sqid]
                draft.update_metadata(
                    {
                        qid: old_value
                    }
                )
    if test:
        from scripts.tests.test_migrate_metadata_for_uploaders import check_migration  # noqa
        check_migration(orig_data, draft)

    draft.save()

def main(dry_run=False, test=False):
    with TokuTransaction():
        prereg_drafts = DraftRegistration.find(
            Q('registration_schema', 'eq', PREREG_SCHEMA)
        )
        for draft in prereg_drafts:
            migrate_draft_metadata(draft, test)
        if dry_run:
            raise RuntimeError("Dry run, rolling back transaction")

if __name__ == '__main__':
    dry = 'dry' in sys.argv
    if not dry:
        script_utils.add_file_logger(logger, __file__)
    test = 'test' in sys.argv
    main(dry, test)

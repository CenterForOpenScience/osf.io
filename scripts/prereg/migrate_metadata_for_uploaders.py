"""
A script to migrate draft registration metadata on Prereg Challenge submissions. The structure of some schema items
has changed to include optional file uploads, and existing file upload values need to be updated.
"""
from modularodm import Q
from modularodm.exceptions import NoResultsFound
import re
from copy import deepcopy

from framework.transactions.context import TokuTransaction

from website.models import (
    MetaSchema,
    DraftRegistration,
    Node
)
from website.files.models import osfstorage

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
        r'/project/(?P<node_id>\w+)/files/osfstorage/(?P<path>\w+)$',
        view_url
    )
    if not match:
        raise RuntimeError
    else:
        items = match.groupdict()
        return items['node_id'], items['path']

def migrate_draft_metadata(draft):
    for question in PREREG_QUESTIONS:
        qid = question['qid']
        qtype = question['type']
        metadata_value = deepcopy(draft.registration_metadata.get(qid, {}))
        if qtype == 'osf-upload':
            if not metadata_value['value']:
                continue  # no file selected
            extra = metadata_value.get('extra')
            if extra:
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
            if not isinstance(metadata_value['value'], dict):  # uploader added to question
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
                if prop['type'] == 'osf-upload':
                    value = metadata_value.get('value', {})
                    if not value:
                        continue  # no file selected
                    try:
                        uid, uploader = [(k, v) for k, v in value.items() if 'uploader' in k][0]
                    except IndexError:
                        pass  # TODO
                    extra = uploader.get('extra')
                    old_value = deepcopy(draft.registration_metadata[qid])
                    if not extra:
                        del old_value['value'][uid]
                        old_value['value']['uploader'] = {}
                    else:
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
                    draft.update_metadata(
                        {
                            qid: old_value
                        }
                    )
    draft.save()

def main(dry_run=False):
    with TokuTransaction():
        prereg_drafts = DraftRegistration.find(
            Q('registration_schema', 'eq', PREREG_SCHEMA)
        )
        for draft in prereg_drafts:
            migrate_draft_metadata(draft)
        if dry_run:
            raise RuntimeError("Dry run, rolling back transaction")

if __name__ == '__main__':
    import sys
    init_app(set_backends=True, routes=False)
    dry = 'dry' in sys.argv
    main(dry)

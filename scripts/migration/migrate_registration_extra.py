"""
Changes existing question.extra on Prereg registrations
to a list. Required for multiple files attached to a question
"""
import sys
import logging

from modularodm import Q
from website.app import init_app
from website.files.models import FileNode, TrashedFileNode
from scripts import utils as scripts_utils
from website.models import Node
from website.prereg.utils import get_prereg_schema
from framework.transactions.context import TokuTransaction


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def migrate_file_representation(bad_file):
    logger.info('Migrating file representation of File: {0}'.format(bad_file))
    view_url = bad_file['viewUrl'].rstrip('/')
    fid = view_url.split('/')[-1]
    fnode = FileNode.load(fid)
    if fnode is None:
        fnode = TrashedFileNode.load(fid)
    assert fnode is not None, 'Could not load FileNode or TrashedFileNode with id {}'.format(fid)
    data = {
        'data': {
            'kind': 'file',
            'name': bad_file['selectedFileName'],
            'path': fnode.path,
            'extra': {},
            'sha256': fnode.versions[-1].metadata['sha256']
        }
    }
    bad_file.update(data)


def migrate_file_meta(question):
    files = question.get('extra')
    migrated = False
    if files and isinstance(files, list):
        for f in files:
            if 'viewUrl' in f:
                if not f.get('data', None):
                    migrate_file_representation(f)
                    migrated = True
    if isinstance(files, dict):
        if len(files) == 0:
            question['extra'] = []
        else:
            question['extra'] = [files]
        migrated = True
    return migrated


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
            logger.info('Migrated preregistration with id: {0}'.format(reg._id))
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

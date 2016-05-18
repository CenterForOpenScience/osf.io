"""
Changes existing question.extra on a draft to a list
required for multiple files attached to a question
"""
import sys
import logging

from modularodm import Q
from website.app import init_app
from website.files.models import FileNode, TrashedFileNode
from scripts import utils as scripts_utils
from website.models import DraftRegistration
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
    if fnode is None:
        logger.error('Could not load FileNode or TrashedFileNode with id {}. Skipping...'.format(fid))
        return
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

def migrate_drafts(dry):
    PREREG_CHALLENGE_METASCHEMA = get_prereg_schema()
    draft_registrations = DraftRegistration.find(
        Q('registration_schema', 'eq', PREREG_CHALLENGE_METASCHEMA)
    )
    count = 0
    for r in draft_registrations:
        # NOTE: We don't query Q('approval', 'eq', None) just in case
        # approval is set but the fk doesn't exist in the database
        if r.approval or r.registered_node:
            continue
        logger.debug('Reading draft with id: {0}'.format(r._id))
        data = r.registration_metadata
        migrated = False
        for q, ans in data.iteritems():
            if isinstance(ans.get('value'), dict):
                for value in ans['value'].values():
                    migrated = migrate_file_meta(value)
            else:
                migrated = migrate_file_meta(ans)
        if migrated:
            count += 1
            logger.info('Migrated draft with id: {0}'.format(r._id))
        if not dry:
            r.save()
    logger.info('Done with {0} drafts migrated.'.format(count))


def main(dry=True):
    init_app(set_backends=True, routes=False)
    if not dry:
        scripts_utils.add_file_logger(logger, __file__)
    migrate_drafts(dry)


if __name__ == '__main__':
    dry_run = '--dry' in sys.argv
    with TokuTransaction():
        main(dry=dry_run)
        if dry_run:
            raise RuntimeError('Dry run, rolling back transaction.')

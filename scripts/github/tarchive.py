import argparse
import os
import tarfile
import tempfile

import django
from django.db import transaction
from django.utils import timezone
import github3

django.setup()

from addons.github import settings as github_settings
from osf.management.commands.force_archive import verify, complete_archive_target
from osf.models import Registration
from scripts import utils as script_utils
from website.util import waterbutler_api_url_for

logger = logging.getLogger(__name__)

DRY_RUN = False
TMP_PATH = tempfile.mkdtemp()
TAR_PATH = '{}/repo.tar.gz'.format(TMP_PATH)
EXTRACTED_PATH = '{}/extracted/'.format(TMP_PATH)

def recursive_upload(dst, fs_path, parent, name=None):
    is_folder = os.path.isdir(fs_path)
    name = name or fs_path.rstrip('/')[-1]
    params = {
        'cookie': dst.creator.get_or_create_cookie(),
        'kind': 'folder' if is_folder else 'file',
        'name': name
    }
    url = waterbutler_api_url_for(dst._id, 'osfstorage', parent.path, _internal=True, **params)
    logger.info('Preparing to upload {} {}'.format(params['kind'], params['name']))
    if not DRY_RUN:
        if is_folder:
            resp = requests.put(url)
            assert resp.status_code == 201
            logger.info('Folder upload complete')
            new_filenode = parent.children.get(name=name)
            for child in os.listdir(fs_path):
                recursive_upload(dst, child, new_filenode)
        else:
            with open(fs_path, 'r+') as fp:
                resp = requests.put(url, data=fp)
                assert resp.status_code == 201
            logger.info('File upload complete')

def tarchive(reg_id):
    start_time = timezone.now()
    dst = Registration.load(reg_id)
    if not dst or not dst.archiving:
        raise Exception('Invalid registration _id')
    assert verify(dst), 'Unable to verify registration'
    target = dst.archive_job.get_target('github')
    if not target or target.done:
        raise Exception('Invalid archive job target')
    src = dst.registered_from
    ghns = src.get_addon('github')
    cli = github3.login(token=ghns.external_account.oauth_key)
    cli.set_client_id(github_settings.CLIENT_ID, github_settings.CLIENT_SECRET)
    repo = cli.repository(ghns.user, ghns.repo)
    logger.info('Downloading tarball of repository...')
    assert repo.archive('tarball', TAR_PATH)
    logger.info('Download complete.')
    with tarfile.open(TAR_PATH) as tf:
        logger.info('Extracting tarball to {} ...'.format(EXTRACTED_PATH))
        tf.extractall(EXTRACTED_PATH)
        logger.info('Extraction complete.')
    logger.info('Preparing node for upload...')
    if dst.files.exclude(type='osf.trashedfolder').filter(name=node_settings.archive_folder_name.replace('/', '-')).exists():
        dst.files.exclude(type='osf.trashedfolder').get(name=node_settings.archive_folder_name.replace('/', '-')).delete()
    logger.info('Preparing to upload...')
    dst_osfs = dst.get_addon('osfstorage')
    recursive_upload(reg, EXTRACTED_PATH, dst_osfs.get_root(), name=dst_osfs.archive_folder_name)
    logger.info('Archive upload complete\nMarking target as archived...')
    complete_archive_target(dst, 'github')
    if reg.logs.filter(date__gte=start_time).exists():
        logger.info('Cleaning up logs...')
        reg.logs.filter(date__gte=start_time).update(should_hide=True)

def parse_args():
    parser = argparse.ArgumentParser(description='Download a tarball of a node\'s GitHub repo and archive it.')
    parser.add_argument('--r', '--registration', dest='reg', type=str, required=True, help='Registration GUID to archive.')
    parser.add_argument('--dry', dest='dry', action='stre_true', help='Dry run.')
    return parser.parse_args()

def main():
    global DRY_RUN
    args = parse_args()
    DRY_RUN = args.dry
    if not DRY_RUN:
        script_utils.add_file_logger(logger, __file__)
    with transaction.atomic():
        tarchive(reg)
        if DRY_RUN:
            raise Exception('Dry run -- transaction rolled back')

if __name__ == "__main__":
    main()

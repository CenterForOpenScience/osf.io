#!/usr/bin/env python
# encoding: utf-8
"""Copy files from previous OSF storage to new OSF storage. Important: settings
must be *exactly* the same as in the production upload service, else files
could be uploaded to the wrong place.
"""

import os
import hashlib
import logging
import subprocess
from cStringIO import StringIO

import requests

from modularodm import Q

from framework.transactions.context import TokuTransaction

from website import settings
from website.app import init_app
from website.models import Node

from website.addons.osffiles.model import NodeFile

from website.addons.osfstorage import model
from website.addons.osfstorage import utils
from website.addons.osfstorage import errors

from scripts import utils as script_utils
from scripts.osfstorage.utils import ensure_osf_files
from scripts.osfstorage import settings as scripts_settings


logger = logging.getLogger(__name__)
script_utils.add_file_logger(logger, __file__)
logging.basicConfig(level=logging.INFO)

client = scripts_settings.STORAGE_CLIENT_CLASS(
    **scripts_settings.STORAGE_CLIENT_OPTIONS
)
container = client.create_container(scripts_settings.STORAGE_CONTAINER_NAME)


class SizeMismatchError(Exception):
    pass

class HashMismatchError(Exception):
    pass


def check_node(node):
    """Check whether git repo for node is intact.
    """
    if not node.files_current:
        return True
    try:
        with open(os.devnull, 'w') as fnull:
            subprocess.check_call(
                ['git', 'log'],
                cwd=os.path.join(settings.UPLOADS_PATH, node._id),
                stdout=fnull,
                stderr=fnull,
            )
        return True
    except subprocess.CalledProcessError:
        return False
    except OSError:
        return False


def get_source_node(node):
    """Recursively search for source node (`registered_from` or `forked_from`),
    excluding corrupt nodes.
    """
    source = node.registered_from or node.forked_from
    if source is None:
        return None
    if check_node(source):
        return source
    return get_source_node(source)


def migrate_version(idx, node_file, node_settings, node=None, dry_run=True):
    """Migrate a legacy file version to OSF Storage. If `node` is provided, use
    instead of the `Node` attached to `node_settings`; used when the git repo
    for the current node is missing or corrupt.

    :param int idx: Version index (zero-based)
    :param NodeFile node_file: Legacy file record
    :param OsfStorageNodeSettings node_settings: Node settings
    :param Node node: Optional source node
    """
    node = node or node_settings.owner
    logger.info('Migrating version {0} from NodeFile {1} on node {2}'.format(
        idx,
        node_file._id,
        node._id,
    ))
    content = scripts_settings.SPECIAL_CASES.get((node._id, node_file._id))
    if content is None:
        content, _ = node.read_file_object(node_file)
    logger.info('Loaded content with length {0}: {1}...'.format(len(content), content[:10]))
    if dry_run:
        return
    record = model.OsfStorageFileRecord.get_or_create(node_file.path, node_settings)
    if len(record.versions) > idx:
        return
    md5 = hashlib.md5(content).hexdigest()
    file_pointer = StringIO(content)
    hash_str = scripts_settings.UPLOAD_PRIMARY_HASH(content).hexdigest()
    obj = container.get_or_upload_file(file_pointer, hash_str)
    if obj.size != len(content):
        raise SizeMismatchError
    if obj.md5 != md5:
        raise HashMismatchError
    metadata = {
        'size': obj.size,
        'content_type': obj.content_type,
        'date_modified': obj.date_modified.isoformat(),
        'md5': md5,
    }
    try:
        record.create_pending_version(node_file.uploader, hash_str)
    except errors.OsfStorageError:
        latest_version = record.get_version(required=True)
        record.remove_version(latest_version)
        record.create_pending_version(node_file.uploader, hash_str)
    record.resolve_pending_version(
        hash_str,
        obj.location,
        metadata,
        log=False,
    )


def migrate_node(node, dry_run=True):
    """Migrate legacy files for a node. If the git repo for the node is corrupt,
    attempt to use its source node (registration or fork) instead.
    """
    logger.info('Migrating node {0}'.format(node._id))
    node_settings = node.get_or_add_addon('osfstorage', auth=None, log=False)
    repo_intact = check_node(node)
    source_node = None
    if not repo_intact:
        logger.warn('Original node {0} is corrupt; attempting to recover'.format(node._id))
        source_node = get_source_node(node)
        if source_node is None:
            logger.error('Could not identify source node for recovery on node {0}'.format(node._id))
    for path, versions in node.files_versions.iteritems():
        for idx, version in enumerate(versions):
            try:
                node_file = NodeFile.load(version)
                migrate_version(idx, node_file, node_settings, node=source_node, dry_run=dry_run)
            except Exception as error:
                logger.error('Could not migrate object {0} on node {1}'.format(version, node._id))
                logger.exception(error)
                break


def get_nodes():
    return Node.find(Q('files_versions', 'ne', None))


def main(dry_run=True):
    nodes = get_nodes()
    logger.info('Migrating files on {0} `Node` records'.format(len(nodes)))
    for node in nodes:
        try:
            with TokuTransaction():
                migrate_node(node, dry_run=dry_run)
        except Exception as error:
            logger.error('Could not migrate node {0}'.format(node._id))
            logger.exception(error)


if __name__ == '__main__':
    import sys
    dry_run = 'dry' in sys.argv
    ensure_osf_files(settings)
    init_app(set_backends=True, routes=False)
    main(dry_run=dry_run)


# Hack: Must configure add-ons before importing `OsfTestCase`
ensure_osf_files(settings)

from nose.tools import *  # noqa

from tests.base import OsfTestCase
from tests.factories import ProjectFactory

import shutil

from framework.auth import Auth


# Important: These tests copy real data to the cloud backend
class TestMigrateFiles(OsfTestCase):

    def setUp(self):
        super(TestMigrateFiles, self).setUp()
        self.project = ProjectFactory()
        self.user = self.project.creator
        self.auth_obj = Auth(user=self.user)
        self.project.delete_addon('osfstorage', auth=None, _force=True)
        for idx in range(5):
            content = 'i want {0} pizzas'.format(idx)
            self.project.add_file(
                auth=self.auth_obj,
                file_name='pizza.md',
                content=content,
                size=len(content),
                content_type='text/markdown',
            )

    def check_record(self, record):
        assert_true(record)
        assert_equal(len(record.versions), 5)
        for idx, version in enumerate(record.versions):
            assert_false(version.pending)
            expected = 'i want {0} pizzas'.format(idx)
            download_url = utils.get_download_url(idx + 1, version, record)
            resp = requests.get(download_url)
            assert_equal(expected, resp.content)

    def test_migrate(self):
        main(dry_run=False)
        node_settings = self.project.get_addon('osfstorage')
        assert_true(node_settings)
        record = model.OsfStorageFileRecord.find_by_path('pizza.md', node_settings)
        self.check_record(record)
        # Test idempotence of migration
        main(dry_run=False)
        assert_equal(len(record.versions), 5)

    def test_migrate_incomplete(self):
        node_settings = self.project.get_or_add_addon('osfstorage', auth=None, log=False)
        record = model.OsfStorageFileRecord.get_or_create('pizza.md', node_settings)
        node_file = NodeFile.load(self.project.files_versions['pizza_md'][0])
        content, _ = self.project.read_file_object(node_file)
        file_pointer = StringIO(content)
        hash_str = scripts_settings.UPLOAD_PRIMARY_HASH(content).hexdigest()
        record.create_pending_version(node_file.uploader, hash_str)
        main(dry_run=False)

    def test_migrate_fork(self):
        fork = self.project.fork_node(auth=self.auth_obj)
        main(dry_run=False)
        node_settings = self.project.get_addon('osfstorage')
        record = model.OsfStorageFileRecord.find_by_path('pizza.md', node_settings)
        self.check_record(record)
        fork_node_settings = fork.get_addon('osfstorage')
        fork_record = model.OsfStorageFileRecord.find_by_path('pizza.md', fork_node_settings)
        self.check_record(fork_record)

    def test_migrate_corrupt_fork_repo_deleted(self):
        fork = self.project.fork_node(auth=self.auth_obj)
        fork_repo = os.path.join(settings.UPLOADS_PATH, fork._id)
        shutil.rmtree(fork_repo)
        main(dry_run=False)
        node_settings = self.project.get_addon('osfstorage')
        record = model.OsfStorageFileRecord.find_by_path('pizza.md', node_settings)
        self.check_record(record)
        fork_node_settings = fork.get_addon('osfstorage')
        fork_record = model.OsfStorageFileRecord.find_by_path('pizza.md', fork_node_settings)
        self.check_record(fork_record)

    def test_migrate_corrupt_fork_git_dir_deleted(self):
        fork = self.project.fork_node(auth=self.auth_obj)
        fork_git_dir = os.path.join(settings.UPLOADS_PATH, fork._id, '.git')
        shutil.rmtree(fork_git_dir)
        main(dry_run=False)
        node_settings = self.project.get_addon('osfstorage')
        record = model.OsfStorageFileRecord.find_by_path('pizza.md', node_settings)
        self.check_record(record)
        fork_node_settings = fork.get_addon('osfstorage')
        fork_record = model.OsfStorageFileRecord.find_by_path('pizza.md', fork_node_settings)
        self.check_record(fork_record)

#!/usr/bin/env python
# encoding: utf-8
"""Copy files from previous OSF storage to new OSF storage. Important: settings
must be *exactly* the same as in the production upload service, else files
could be uploaded to the wrong place.
"""

from cStringIO import StringIO

import requests

from modularodm import Q

from website import settings
from website.app import init_app
from website.models import Node

from website.addons.osffiles.model import NodeFile

from website.addons.osfstorage import model
from website.addons.osfstorage import utils

from scripts.osfstorage import settings as scripts_settings


client = scripts_settings.STORAGE_CLIENT_CLASS(
    **scripts_settings.STORAGE_CLIENT_OPTIONS
)
container = client.get_container(scripts_settings.STORAGE_CONTAINER_NAME)


def migrate_version(node_file, node_settings):
    node = node_settings.owner
    record = model.FileRecord.get_or_create(node_file.path, node_settings)
    content, _ = node.read_file_object(node_file)
    file_pointer = StringIO(content)
    hash_str = scripts_settings.UPLOAD_PRIMARY_HASH(content).hexdigest()
    obj = container.upload_file(file_pointer, hash_str)
    version = model.FileVersion(
        creator=node_file.uploader,
        date_modified=node_file.date_modified,
    )
    version.status = model.status['COMPLETE']
    version.location = obj.location
    version.size = obj.size
    version.save()
    record.versions.append(version)
    record.save()


def migrate_node(node):
    node_settings = node.get_or_add_addon('osfstorage', auth=None, log=False)
    for path, versions in node.files_versions.iteritems():
        for version in versions:
            try:
                node_file = NodeFile.load(version)
            except Exception as error:
                logger.error('Could not migrate object {0}'.format(node_file._id))
                logger.exception(error)
                break
            migrate_version(node_file, node_settings)


def get_nodes():
    return Node.find(Q('files_versions', 'ne', None))


def main():
    nodes = get_nodes()
    for node in nodes:
        migrate_node(node)


if __name__ == '__main__':
    init_app()
    main()


from nose.tools import *  # noqa

from tests.base import OsfTestCase
from tests.factories import ProjectFactory

from framework.auth import Auth


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

    def test_migrate(self):
        main()
        node_settings = self.project.get_addon('osfstorage')
        assert_true(node_settings)
        record = model.FileRecord.find_by_path('pizza.md', node_settings)
        assert_true(record)
        assert_equal(len(record.versions), 5)
        for idx, version in enumerate(record.versions):
            expected = 'i want {0} pizzas'.format(idx)
            download_url = utils.get_download_url(version)
            resp = requests.get(download_url)
            assert_equal(expected, resp.content)

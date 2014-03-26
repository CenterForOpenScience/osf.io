# -*- coding: utf-8 -*-
"""Tests for website.addons.dropbox.utils."""
from nose.tools import *  # PEP8 asserts

from framework.auth.decorators import Auth
from website.project.model import NodeLog

from tests.base import DbTestCase
from tests.factories import ProjectFactory

from website.addons.dropbox.tests.factories import DropboxFileFactory
from website.addons.dropbox.tests.utils import DropboxAddonTestCase, mock_responses
from website.app import init_app
from website.addons.dropbox import utils
from website.addons.dropbox.views.config import serialize_folder

app = init_app(set_backends=False, routes=True)


class TestNodeLogger(DropboxAddonTestCase):

    def test_log_file_added(self):
        df = DropboxFileFactory()
        logger = utils.DropboxNodeLogger(node=self.project,
            auth=Auth(self.user), file_obj=df)
        with self.app.app.test_request_context():
            logger.log(NodeLog.FILE_ADDED, save=True)

        last_log = self.project.logs[-1]

        assert_equal(last_log.action, "dropbox_{0}".format(NodeLog.FILE_ADDED))


def test_get_file_name():
    assert_equal(utils.get_file_name('foo/bar/baz.txt'), 'baz.txt')
    assert_equal(utils.get_file_name('/foo/bar/baz.txt'), 'baz.txt')
    assert_equal(utils.get_file_name('/foo/bar/baz.txt/'), 'baz.txt')


def test_clean_path():
    assert_equal(utils.clean_path('/'), '')
    assert_equal(utils.clean_path('/foo/bar/baz/'), 'foo/bar/baz')
    assert_equal(utils.clean_path(None), '')


def test_serialize_folder():
    metadata = {

    }
    assert 0, 'finish me'


class TestBuildDropboxUrls(DbTestCase):

    def test_build_dropbox_urls_file(self):
        node = ProjectFactory()
        fake_metadata = mock_responses['metadata_single']
        with app.test_request_context():
            result = utils.build_dropbox_urls(fake_metadata, node)
            path = utils.clean_path(fake_metadata['path'])
            assert_equal(result['download'],
                node.web_url_for('dropbox_download', path=path))
            assert_equal(result['view'],
                node.web_url_for('dropbox_view_file', path=path))
            assert_equal(result['delete'],
                node.api_url_for('dropbox_delete_file', path=path))

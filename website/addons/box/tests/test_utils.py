# -*- coding: utf-8 -*-
"""Tests for website.addons.box.utils."""
import os

from nose.tools import *  # noqa (PEP8 asserts)

from framework.auth import Auth
from website.project.model import NodeLog

from tests.base import OsfTestCase
from tests.factories import ProjectFactory

from website.addons.box.tests.factories import BoxFileFactory
from website.addons.box.tests.utils import BoxAddonTestCase, mock_responses
from website.addons.box import utils
from website.addons.box.views.config import serialize_folder


class TestNodeLogger(BoxAddonTestCase):

    def test_log_file_added(self):
        df = BoxFileFactory()
        logger = utils.BoxNodeLogger(
            node=self.project,
            auth=Auth(self.user),
            file_obj=df
        )
        logger.log(NodeLog.FILE_ADDED, save=True)

        last_log = self.project.logs[-1]

        assert_equal(last_log.action, "box_{0}".format(NodeLog.FILE_ADDED))

    # Regression test for https://github.com/CenterForOpenScience/osf.io/issues/1557
    def test_log_deauthorized_when_node_settings_are_deleted(self):
        project = ProjectFactory()
        project.add_addon('box', auth=Auth(project.creator))
        dbox_settings = project.get_addon('box')
        dbox_settings.delete(save=True)
        # sanity check
        assert_true(dbox_settings.deleted)

        logger = utils.BoxNodeLogger(node=project, auth=Auth(self.user))
        logger.log(action='node_deauthorized', save=True)

        last_log = project.logs[-1]
        assert_equal(last_log.action, 'box_node_deauthorized')


# FIXME(sloria): This test is incorrect. The mocking needs work.
# class TestRenderFile(OsfTestCase):

#     @mock.patch('website.addons.box.client.BoxClient.get_file_and_metadata')
#     def test_render_box_file_when_file_has_taken_down_by_dmca(self, mock_get_file):
#         mock_resp = mock.Mock(spec=BoxResponse)
#         mock_resp.reason = 'This file is no longer available due to a takedown request under the Digital Millennium Copyright Act'
#         mock_resp.status = 461
#         mock_client = mock.Mock(spec=BoxClient)
#         mock_client.get_file_and_metadata.side_effect = ErrorResponse(mock_resp, 'DMCA takedown')
#         with patch_client('website.addons.box.utils.get_node_addon_client', mock_client=mock_client):
#             f = BoxFileFactory()
#             result = utils.render_box_file(f, client=mock_client)


# TODO(mfraezz): Add support for folder sharing urls
# def test_get_share_folder_uri():
#     expected = 'https://box.com/home/foo?shareoptions=1&share_subfolder=0&share=1'
#     assert_equal(utils.get_share_folder_uri('/foo/'), expected)
#     assert_equal(utils.get_share_folder_uri('foo'), expected)


def test_serialize_folder():
    metadata = {
        u'bytes': 0,
        u'icon': u'folder',
        u'is_dir': True,
        u'modified': u'Sat, 22 Mar 2014 05:40:29 +0000',
        u'path': u'/datasets/New Folder',
        u'rev': u'3fed51f002c12fc',
        u'revision': 67032351,
        u'root': u'box',
        u'size': u'0 bytes',
        u'thumb_exists': False
    }
    result = serialize_folder(metadata)
    assert_equal(result['path'], metadata['path'])
    assert_equal(result['name'], 'Box' + metadata['path'])


class TestBuildBoxUrls(OsfTestCase):

    def test_build_box_urls_file(self):
        node = ProjectFactory()
        fake_metadata = mock_responses['metadata_single']
        fake_metadata['type'] = 'folder'
        result = utils.build_box_urls(fake_metadata, node)
        path = fake_metadata['path']
        assert_equal(
            result['folders'],
            node.api_url_for(
                'box_hgrid_data_contents',
                folder_id=fake_metadata['id'],
                foldersOnly=1
            )
        )

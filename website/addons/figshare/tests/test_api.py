# -*- coding: utf-8 -*-
import os
import mock

from nose.tools import *  # noqa (PEP8 asserts)
from tests.base import OsfTestCase
from tests.factories import NodeFactory

from framework.auth.core import Auth
from website.addons.figshare.model import AddonFigShareNodeSettings
from website.addons.figshare.api import _get_project_url, Figshare

class TestFigshareAPIWrapper(OsfTestCase):

    def setUp(self):
        OsfTestCase.setUp(self)
        self.node = NodeFactory()
        self.node.add_addon('figshare', auth=Auth(self.node.creator))
        self.node.save()
        self.node_settings = self.node.get_addon('figshare')
        self.client = Figshare()

    def test_get_project_url(self):
        url = _get_project_url(self.node_settings, 123)
        expected = os.path.join(self.node_settings.api_url, 'projects', '123')
        assert_equal(url, expected)

    # Regression test
    @mock.patch('website.addons.figshare.api.Figshare._send')
    def test_add_article_to_project_called_with_correct_url(self, mock_send):
        self.client.add_article_to_project(self.node_settings, 123, 'foo')
        url = _get_project_url(self.node_settings, 123, 'articles')
        assert_equal(mock_send.call_args[0][0], url)

    @mock.patch('website.addons.figshare.api.Figshare._send')
    def test_remove_article_from_project_called_with_correct_url(self, mock_send):
        self.client.add_article_to_project(self.node_settings, 123, 'foo')
        url = _get_project_url(self.node_settings, 123, 'articles')
        assert_equal(mock_send.call_args[0][0], url)

    @mock.patch('website.addons.figshare.api.Figshare._send')
    def test_delete_project_called_with_correct_url(self, mock_send):
        self.client.delete_project(self.node_settings, 123)
        url = _get_project_url(self.node_settings, 123)
        assert_equal(mock_send.call_args[0][0], url)

    @mock.patch('website.addons.figshare.api.Figshare._send')
    def test_create_project_called_with_correct_url(self, mock_send):
        self.client.create_project(self.node_settings, 123)
        url = _get_project_url(self.node_settings, '').rstrip('/')
        assert_equal(mock_send.call_args[0][0], url)

    @mock.patch('website.addons.figshare.api.Figshare._send')
    def test_get_project_collaborators(self, mock_send):
        self.client.get_project_collaborators(self.node_settings, 123)
        url = _get_project_url(self.node_settings, 123, 'collaborators')
        assert_equal(mock_send.call_args[0][0], url)

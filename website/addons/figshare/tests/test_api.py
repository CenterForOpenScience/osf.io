# -*- coding: utf-8 -*-
import os

from nose.tools import *  # noqa (PEP8 asserts)
from tests.base import OsfTestCase
from tests.factories import NodeFactory

from framework.auth.core import Auth
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

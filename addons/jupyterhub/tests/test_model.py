import mock
from nose.tools import *  # noqa
import pytest
import unittest

from tests.base import get_default_metaschema
from osf_tests.factories import ProjectFactory

from framework.auth import Auth
from addons.jupyterhub.models import NodeSettings
from addons.jupyterhub.tests.factories import JupyterhubNodeSettingsFactory


pytestmark = pytest.mark.django_db

class TestNodeSettings(unittest.TestCase):
    short_name = 'jupyterhub'
    full_name = 'JupyterHub'
    NodeSettingsFactory = JupyterhubNodeSettingsFactory

    def setUp(self):
        super(TestNodeSettings, self).setUp()
        self.node = ProjectFactory()
        self.user = self.node.creator

        self.node_settings = self.NodeSettingsFactory(owner=self.node)
        self.node_settings.save()

    def tearDown(self):
        super(TestNodeSettings, self).tearDown()
        self.node_settings.remove()
        self.node.remove()
        self.user.remove()

    def test_set_services(self):
        self.node_settings.set_services([('jh1', 'https://jh1.test/')])
        self.node_settings.save()
        # Container was set
        assert_equal(self.node_settings.get_services(),
                     [('jh1', 'https://jh1.test/')])

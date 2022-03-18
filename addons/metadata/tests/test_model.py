import mock
from nose.tools import *  # noqa
import pytest
import unittest

from tests.base import get_default_metaschema
from osf_tests.factories import ProjectFactory

from framework.auth import Auth
from ..models import NodeSettings
from .factories import NodeSettingsFactory


pytestmark = pytest.mark.django_db

class TestNodeSettings(unittest.TestCase):
    _NodeSettingsFactory = NodeSettingsFactory

    def setUp(self):
        super(TestNodeSettings, self).setUp()
        self.node = ProjectFactory()
        self.user = self.node.creator

        self.node_settings = self._NodeSettingsFactory(owner=self.node)
        self.node_settings.save()

    def tearDown(self):
        super(TestNodeSettings, self).tearDown()
        self.node.delete()
        self.user.delete()

    def test_set_param_1(self):
        self.node_settings.set_param_1('TEST_PARAM_1')
        self.node_settings.save()
        assert_equal(self.node_settings.get_param_1(), 'TEST_PARAM_1')

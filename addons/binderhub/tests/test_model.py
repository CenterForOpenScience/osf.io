import mock
from nose.tools import *  # noqa
import pytest
import unittest

from tests.base import get_default_metaschema
from osf_tests.factories import UserFactory, ProjectFactory

from framework.auth import Auth
from ..models import NodeSettings
from .. import settings
from .factories import UserSettingsFactory, NodeSettingsFactory, make_binderhub


pytestmark = pytest.mark.django_db

class TestUserSettings(unittest.TestCase):
    _UserSettingsFactory = UserSettingsFactory

    def setUp(self):
        super(TestUserSettings, self).setUp()
        self.user = UserFactory()

        self.user_settings = self._UserSettingsFactory(owner=self.user)
        self.user_settings.save()

    def tearDown(self):
        super(TestUserSettings, self).tearDown()
        self.user.delete()

    def test_default_binderhubs(self):
        self.user_settings.save()
        assert_equal(len(self.user_settings.get_binderhubs()), 0)

    def test_single_binderhubs(self):
        self.user_settings.set_binderhubs([
            make_binderhub(binderhub_url='https://testa.my.site',
                           binderhub_oauth_client_secret='MY_CUSTOM_SECRET',)
        ])
        self.user_settings.save()
        binderhubs = self.user_settings.get_binderhubs(allow_secrets=True)
        assert_equal(len(binderhubs), 1)
        assert_equal(binderhubs[0]['binderhub_url'], 'https://testa.my.site')
        assert_equal(binderhubs[0]['binderhub_oauth_client_secret'], 'MY_CUSTOM_SECRET')
        binderhubs = self.user_settings.get_binderhubs(allow_secrets=False)
        assert_equal(len(binderhubs), 1)
        assert_equal(binderhubs[0]['binderhub_url'], 'https://testa.my.site')
        assert_not_in('binderhub_oauth_client_secret', binderhubs[0])

    def test_multiple_binderhubs(self):
        self.user_settings.set_binderhubs([
            make_binderhub(binderhub_url='https://testa.my.site',
                           binderhub_oauth_client_secret='MY_CUSTOM_SECRET_A',),
            make_binderhub(binderhub_url='https://testb.my.site',
                           binderhub_oauth_client_secret='MY_CUSTOM_SECRET_B',),
        ])
        self.user_settings.save()
        binderhubs = self.user_settings.get_binderhubs(allow_secrets=True)
        assert_equal(len(binderhubs), 2)
        assert_equal(binderhubs[0]['binderhub_url'], 'https://testa.my.site')
        assert_equal(binderhubs[0]['binderhub_oauth_client_secret'], 'MY_CUSTOM_SECRET_A')
        assert_equal(binderhubs[1]['binderhub_url'], 'https://testb.my.site')
        assert_equal(binderhubs[1]['binderhub_oauth_client_secret'], 'MY_CUSTOM_SECRET_B')
        binderhubs = self.user_settings.get_binderhubs(allow_secrets=False)
        assert_equal(len(binderhubs), 2)
        assert_equal(binderhubs[0]['binderhub_url'], 'https://testa.my.site')
        assert_not_in('binderhub_oauth_client_secret', binderhubs[0])
        assert_equal(binderhubs[1]['binderhub_url'], 'https://testb.my.site')
        assert_not_in('binderhub_oauth_client_secret', binderhubs[1])

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

    def test_set_binder_url(self):
        self.node_settings.set_binder_url('https://binder.my.site')
        self.node_settings.save()
        assert_equal(self.node_settings.get_binder_url(), 'https://binder.my.site')

    def test_default_available_binderhubs(self):
        self.node_settings.save()
        binderhubs = self.node_settings.get_available_binderhubs()
        assert_equal(len(binderhubs), 1)
        assert_equal(binderhubs[0]['binderhub_url'], settings.DEFAULT_BINDER_URL)
        assert_not_in('binderhub_oauth_client_secret', binderhubs[0])
        binderhubs = self.node_settings.get_available_binderhubs(allow_secrets=True)
        assert_equal(len(binderhubs), 1)
        assert_equal(binderhubs[0]['binderhub_url'], settings.DEFAULT_BINDER_URL)
        assert_in('binderhub_oauth_client_secret', binderhubs[0])

    def test_default_empty_binderhubs(self):
        self.node_settings.set_available_binderhubs([])
        self.node_settings.save()
        binderhubs = self.node_settings.get_available_binderhubs()
        assert_equal(len(binderhubs), 1)
        assert_equal(binderhubs[0]['binderhub_url'], settings.DEFAULT_BINDER_URL)
        assert_not_in('binderhub_oauth_client_secret', binderhubs[0])
        binderhubs = self.node_settings.get_available_binderhubs(allow_secrets=True)
        assert_equal(len(binderhubs), 1)
        assert_equal(binderhubs[0]['binderhub_url'], settings.DEFAULT_BINDER_URL)
        assert_in('binderhub_oauth_client_secret', binderhubs[0])

    def test_default_empty_binderhubs(self):
        self.node_settings.set_available_binderhubs([])
        self.node_settings.save()
        binderhubs = self.node_settings.get_available_binderhubs()
        assert_equal(len(binderhubs), 1)
        assert_equal(binderhubs[0]['binderhub_url'], settings.DEFAULT_BINDER_URL)
        assert_not_in('binderhub_oauth_client_secret', binderhubs[0])
        binderhubs = self.node_settings.get_available_binderhubs(allow_secrets=True)
        assert_equal(len(binderhubs), 1)
        assert_equal(binderhubs[0]['binderhub_url'], settings.DEFAULT_BINDER_URL)
        assert_in('binderhub_oauth_client_secret', binderhubs[0])

    def test_default_binderhubs(self):
        self.node_settings.set_available_binderhubs([
            make_binderhub(binderhub_url='https://testa.my.site',
                           binderhub_oauth_client_secret='MY_CUSTOM_SECRET_A',),
        ])
        self.node_settings.save()
        binderhubs = self.node_settings.get_available_binderhubs()
        assert_equal(len(binderhubs), 1)
        assert_equal(binderhubs[0]['binderhub_url'], 'https://testa.my.site')
        assert_not_in('binderhub_oauth_client_secret', binderhubs[0])
        binderhubs = self.node_settings.get_available_binderhubs(allow_secrets=True)
        assert_equal(len(binderhubs), 1)
        assert_equal(binderhubs[0]['binderhub_url'], 'https://testa.my.site')
        assert_in('binderhub_oauth_client_secret', binderhubs[0])

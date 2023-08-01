# -*- coding: utf-8 -*-
from nose.tools import assert_in, assert_equal
import mock
import pytest

from rest_framework import status as http_status

from addons.base.tests.views import (
    OAuthAddonAuthViewsTestCaseMixin, OAuthAddonConfigViewsTestCaseMixin
)
from addons.boa.models import BoaProvider
from tests.base import OsfTestCase
from addons.boa.serializer import BoaSerializer
from addons.boa.tests.utils import BoaAddonTestCase

pytestmark = pytest.mark.django_db

class TestAuthViews(OAuthAddonAuthViewsTestCaseMixin, BoaAddonTestCase, OsfTestCase):

    @property
    def Provider(self):
        return BoaProvider

    def test_oauth_start(self):
        pass

    def test_oauth_finish(self):
        pass


class TestConfigViews(BoaAddonTestCase, OAuthAddonConfigViewsTestCaseMixin, OsfTestCase):
    Serializer = BoaSerializer
    client = BoaProvider

    @property
    def folder(self):
        return {'name': '/Documents/', 'path': '/Documents/'}

    def setUp(self):
        super(TestConfigViews, self).setUp()
        self.mock_ser_api = mock.patch('boa.Client.login')
        self.mock_ser_api.start()
        self.set_node_settings(self.node_settings)

    def tearDown(self):
        self.mock_ser_api.stop()
        super(TestConfigViews, self).tearDown()

    @mock.patch('addons.boa.models.NodeSettings.get_folders')
    def test_folder_list(self, mock_connection):
        #test_get_datasets
        mock_connection.return_value = ['/Documents/', '/Pictures/', '/Videos/']

        super(TestConfigViews, self).test_folder_list()

    def test_get_config(self):
        url = self.project.api_url_for(
            '{0}_get_config'.format(self.ADDON_SHORT_NAME))
        res = self.app.get(url, auth=self.user.auth)
        assert_equal(res.status_code, http_status.HTTP_200_OK)
        assert_in('result', res.json)
        serialized = self.Serializer().serialize_settings(
            self.node_settings,
            self.user,
        )
        assert_equal(serialized, res.json['result'])

# -*- coding: utf-8 -*-
import mock
import httplib as http

from nose.tools import (assert_equal, assert_equals,
    assert_true, assert_in, assert_false)
import pytest

from tests.base import OsfTestCase

from addons.base.tests.views import (
    OAuthAddonConfigViewsTestCaseMixin
)
from addons.cloudfiles.tests.utils import CloudFilesAddonTestCase
from addons.cloudfiles.serializer import CloudFilesSerializer
from addons.cloudfiles.tests.utils import MockConnection

pytestmark = pytest.mark.django_db

class TestCloudFilesViews(CloudFilesAddonTestCase, OAuthAddonConfigViewsTestCaseMixin, OsfTestCase):

    def test_set_config(self):
        self.node_settings.set_auth(self.external_account, self.user)
        url = self.project.api_url_for('{0}_set_config'.format(self.ADDON_SHORT_NAME))
        res = self.app.put_json(url, {
            'selected': self.folder,
            'selectedRegion': 'IAD'
        }, auth=self.user.auth)
        assert_equal(res.status_code, http.OK)
        self.project.reload()
        self.node_settings.reload()
        assert_equal(
            self.project.logs.latest().action,
            '{0}_container_linked'.format(self.ADDON_SHORT_NAME)
        )
        assert_equal(res.json['result']['folder']['name'], self.node_settings.folder_name)

    @mock.patch.object(CloudFilesSerializer, 'credentials_are_valid')
    def test_get_config(self, mock_cred):
        mock_cred.return_value = True
        super(TestCloudFilesViews, self).test_get_config()

    @mock.patch('addons.cloudfiles.models.NodeSettings.get_containers')
    def test_folder_list(self, mock_connection):
        mock_connection.return_value = ['container 1', 'container 2', 'container 3']

        self.node_settings.set_auth(self.external_account, self.user)
        self.node_settings.save()
        url = self.project.api_url_for('{0}_folder_list'.format(self.ADDON_SHORT_NAME))
        res = self.app.get(url, auth=self.user.auth, params={'region' : 'IAD'})
        assert_equal(res.status_code, http.OK)


class TestCreateContainer(CloudFilesAddonTestCase, OsfTestCase):

    @mock.patch('rackspace.connection.Connection', return_value=MockConnection)
    def test_create_container(self, mock_conn):
        self.node_settings.set_auth(self.external_account, self.user)
        url = self.project.api_url_for('{0}_create_container'.format(self.ADDON_SHORT_NAME))
        res = self.app.post_json(url, {
            'container_name': "Special chars are √ ",
            'container_location': 'FAK'
        }, auth=self.user.auth)

        assert_equal(res.json, {})
        assert_equal(res.status_code, http.OK)
        # Special chars must be url encoded
        MockConnection.object_store.create_container.assert_called_once_with(name='Special+chars+are+%E2%88%9A+')

    @mock.patch('rackspace.connection.Connection', return_value=MockConnection)
    def test_create_container_empty_string_name(self, mock_conn):
        self.node_settings.set_auth(self.external_account, self.user)
        url = self.project.api_url_for('{0}_create_container'.format(self.ADDON_SHORT_NAME))


        res = self.app.post_json(url, {
            'container_name': "",
            'container_location': 'FAK'
        }, auth=self.user.auth, expect_errors=True)

        assert_equal(res.json, {"message": "Cloud Files container name must contain characters"})
        assert_equal(res.status_code, http.BAD_REQUEST)

    @mock.patch('rackspace.connection.Connection', return_value=MockConnection)
    def test_create_container_bad_chars(self, mock_conn):
        self.node_settings.set_auth(self.external_account, self.user)
        url = self.project.api_url_for('{0}_create_container'.format(self.ADDON_SHORT_NAME))


        res = self.app.post_json(url, {
            'container_name': "? / these are forbidden!",
            'container_location': 'FAK'
        }, auth=self.user.auth, expect_errors=True)

        assert_equal(res.json, {"message":
                                    'Cloud Files container name cannot contain either of the characters: / or ?'})
        assert_equal(res.status_code, http.BAD_REQUEST)

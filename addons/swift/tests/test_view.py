# -*- coding: utf-8 -*-
import httplib as http

import mock
from nose.tools import *  # noqa
from swiftclient import exceptions as swift_exceptions

from framework.auth import Auth
from tests.base import OsfTestCase, get_default_metaschema
from tests.factories import ProjectFactory, AuthUserFactory

from addons.base.tests.views import (
    OAuthAddonConfigViewsTestCaseMixin
)
from addons.swift.tests.utils import SwiftAddonTestCase
from addons.swift.utils import validate_container_name
from website.util import api_url_for


class TestSwiftViews(SwiftAddonTestCase, OAuthAddonConfigViewsTestCaseMixin, OsfTestCase):
    def setUp(self):
        self.mock_can_list = mock.patch('addons.swift.views.utils.can_list')
        self.mock_can_list.return_value = True
        self.mock_can_list.start()
        self.mock_uid = mock.patch('addons.swift.views.utils.get_user_info')
        self.mock_uid.return_value = {'id': '1234567890', 'display_name': 'swift.user'}
        self.mock_uid.start()
        self.mock_exists = mock.patch('addons.swift.views.utils.container_exists')
        self.mock_exists.return_value = True
        self.mock_exists.start()
        super(TestSwiftViews, self).setUp()

    def tearDown(self):
        self.mock_can_list.stop()
        self.mock_uid.stop()
        self.mock_exists.stop()
        super(TestSwiftViews, self).tearDown()

    def test_swift_settings_input_empty_keys(self):
        url = self.project.api_url_for('swift_add_user_account')
        rv = self.app.post_json(url,{
            'auth_version': '',
            'auth_url': '',
            'access_key': '',
            'secret_key': '',
            'tenant_name': ''
        }, auth=self.user.auth, expect_errors=True)
        assert_equals(rv.status_int, http.BAD_REQUEST)
        assert_in('All the fields above are required.', rv.body)

    def test_swift_settings_input_empty_access_key_v2(self):
        url = self.project.api_url_for('swift_add_user_account')
        rv = self.app.post_json(url,{
            'auth_version': '2',
            'auth_url': 'Non-empty-auth-url',
            'access_key': '',
            'secret_key': 'Non-empty-secret-key',
            'tenant_name': 'Non-empty-tenant-name'
        }, auth=self.user.auth, expect_errors=True)
        assert_equals(rv.status_int, http.BAD_REQUEST)
        assert_in('All the fields above are required.', rv.body)

    def test_swift_settings_input_empty_secret_key_v2(self):
        url = self.project.api_url_for('swift_add_user_account')
        rv = self.app.post_json(url,{
            'auth_version': '2',
            'auth_url': 'Non-empty-auth-url',
            'access_key': 'Non-empty-access-key',
            'secret_key': '',
            'tenant_name': 'Non-empty-tenant-name'
        }, auth=self.user.auth, expect_errors=True)
        assert_equals(rv.status_int, http.BAD_REQUEST)
        assert_in('All the fields above are required.', rv.body)

    def test_swift_settings_input_empty_tenant_name_v2(self):
        url = self.project.api_url_for('swift_add_user_account')
        rv = self.app.post_json(url,{
            'auth_version': '2',
            'auth_url': 'Non-empty-auth-url',
            'access_key': 'Non-empty-access-key',
            'secret_key': 'Non-empty-secret-key',
            'tenant_name': ''
        }, auth=self.user.auth, expect_errors=True)
        assert_equals(rv.status_int, http.BAD_REQUEST)
        assert_in('All the fields above are required.', rv.body)

    def test_swift_settings_input_empty_auth_url_v2(self):
        url = self.project.api_url_for('swift_add_user_account')
        rv = self.app.post_json(url,{
            'auth_version': '2',
            'auth_url': '',
            'access_key': 'Non-empty-access-key',
            'secret_key': 'Non-empty-secret-key',
            'tenant_name': 'Non-empty-tenant-name'
        }, auth=self.user.auth, expect_errors=True)
        assert_equals(rv.status_int, http.BAD_REQUEST)
        assert_in('All the fields above are required.', rv.body)

    def test_swift_settings_input_empty_auth_version_v2(self):
        url = self.project.api_url_for('swift_add_user_account')
        rv = self.app.post_json(url,{
            'auth_version': '',
            'auth_url': 'Non-empty-auth-url',
            'access_key': 'Non-empty-access-key',
            'secret_key': 'Non-empty-secret-key',
            'tenant_name': 'Non-empty-tenant-name'
        }, auth=self.user.auth, expect_errors=True)
        assert_equals(rv.status_int, http.BAD_REQUEST)
        assert_in('All the fields above are required.', rv.body)

    def test_swift_settings_input_empty_access_key_v3(self):
        url = self.project.api_url_for('swift_add_user_account')
        rv = self.app.post_json(url,{
            'auth_version': '3',
            'auth_url': 'Non-empty-auth-url',
            'access_key': '',
            'secret_key': 'Non-empty-secret-key',
            'tenant_name': 'Non-empty-tenant-name',
            'user_domain_name': 'Non-empty-user-domain-name',
            'project_domain_name': 'Non-empty-project-domain-name'
        }, auth=self.user.auth, expect_errors=True)
        assert_equals(rv.status_int, http.BAD_REQUEST)
        assert_in('All the fields above are required.', rv.body)

    def test_swift_settings_input_empty_secret_key_v3(self):
        url = self.project.api_url_for('swift_add_user_account')
        rv = self.app.post_json(url,{
            'auth_version': '3',
            'auth_url': 'Non-empty-auth-url',
            'access_key': 'Non-empty-access-key',
            'secret_key': '',
            'tenant_name': 'Non-empty-tenant-name',
            'user_domain_name': 'Non-empty-user-domain-name',
            'project_domain_name': 'Non-empty-project-domain-name'
        }, auth=self.user.auth, expect_errors=True)
        assert_equals(rv.status_int, http.BAD_REQUEST)
        assert_in('All the fields above are required.', rv.body)

    def test_swift_settings_input_empty_tenant_name_v3(self):
        url = self.project.api_url_for('swift_add_user_account')
        rv = self.app.post_json(url,{
            'auth_version': '3',
            'auth_url': 'Non-empty-auth-url',
            'access_key': 'Non-empty-access-key',
            'secret_key': 'Non-empty-secret-key',
            'tenant_name': '',
            'user_domain_name': 'Non-empty-user-domain-name',
            'project_domain_name': 'Non-empty-project-domain-name'
        }, auth=self.user.auth, expect_errors=True)
        assert_equals(rv.status_int, http.BAD_REQUEST)
        assert_in('All the fields above are required.', rv.body)

    def test_swift_settings_input_empty_auth_url_v3(self):
        url = self.project.api_url_for('swift_add_user_account')
        rv = self.app.post_json(url,{
            'auth_version': '3',
            'auth_url': '',
            'access_key': 'Non-empty-access-key',
            'secret_key': 'Non-empty-secret-key',
            'tenant_name': 'Non-empty-tenant-name',
            'user_domain_name': 'Non-empty-user-domain-name',
            'project_domain_name': 'Non-empty-project-domain-name'
        }, auth=self.user.auth, expect_errors=True)
        assert_equals(rv.status_int, http.BAD_REQUEST)
        assert_in('All the fields above are required.', rv.body)

    def test_swift_settings_input_empty_user_domain_name_v3(self):
        url = self.project.api_url_for('swift_add_user_account')
        rv = self.app.post_json(url,{
            'auth_version': '3',
            'auth_url': 'Non-empty-auth-url',
            'access_key': 'Non-empty-access-key',
            'secret_key': 'Non-empty-secret-key',
            'tenant_name': 'Non-empty-tenant-name',
            'user_domain_name': '',
            'project_domain_name': 'Non-empty-project-domain-name'
        }, auth=self.user.auth, expect_errors=True)
        assert_equals(rv.status_int, http.BAD_REQUEST)
        assert_in('The field `user_domain_name` is required when you choose identity V3.', rv.body)

    def test_swift_settings_input_empty_project_domain_name_v3(self):
        url = self.project.api_url_for('swift_add_user_account')
        rv = self.app.post_json(url,{
            'auth_version': '3',
            'auth_url': 'Non-empty-auth-url',
            'access_key': 'Non-empty-access-key',
            'secret_key': 'Non-empty-secret-key',
            'tenant_name': 'Non-empty-tenant-name',
            'user_domain_name': 'Non-empty-user-domain-name',
            'project_domain_name': ''
        }, auth=self.user.auth, expect_errors=True)
        assert_equals(rv.status_int, http.BAD_REQUEST)
        assert_in('The field `project_domain_name` is required when you choose identity V3.', rv.body)

    def test_swift_set_bucket_no_settings(self):
        user = AuthUserFactory()
        self.project.add_contributor(user, save=True)
        url = self.project.api_url_for('swift_set_config')
        res = self.app.put_json(
            url, {'swift_bucket': 'hammertofall'}, auth=user.auth,
            expect_errors=True
        )
        assert_equal(res.status_code, http.BAD_REQUEST)

    def test_swift_set_bucket_no_auth(self):

        user = AuthUserFactory()
        user.add_addon('swift')
        self.project.add_contributor(user, save=True)
        url = self.project.api_url_for('swift_set_config')
        res = self.app.put_json(
            url, {'swift_bucket': 'hammertofall'}, auth=user.auth,
            expect_errors=True
        )
        assert_equal(res.status_code, http.FORBIDDEN)

    def test_swift_set_bucket_registered(self):
        registration = self.project.register_node(
            get_default_metaschema(), Auth(self.user), '', ''
        )

        url = registration.api_url_for('swift_set_config')
        res = self.app.put_json(
            url, {'swift_bucket': 'hammertofall'}, auth=self.user.auth,
            expect_errors=True,
        )

        assert_equal(res.status_code, http.BAD_REQUEST)

    @mock.patch('addons.swift.views.utils.can_list', return_value=False)
    def test_user_settings_cant_list_v2(self, mock_can_list):
        url = api_url_for('swift_add_user_account')
        rv = self.app.post_json(url, {
            'auth_version': '2',
            'auth_url': '1234',
            'access_key': 'aldkjf',
            'secret_key': 'las',
            'tenant_name': 'ten'
        }, auth=self.user.auth, expect_errors=True)
        assert_equals(rv.status_int, http.BAD_REQUEST)
        assert_in('Unable to list containers.', rv.body)

    @mock.patch('addons.swift.views.utils.can_list', return_value=False)
    def test_user_settings_cant_list_v3(self, mock_can_list):
        url = api_url_for('swift_add_user_account')
        rv = self.app.post_json(url, {
            'auth_version': '3',
            'auth_url': '1234',
            'access_key': 'aldkjf',
            'secret_key': 'las',
            'tenant_name': 'ten',
            'user_domain_name': 'Default',
            'project_domain_name': 'Default'
        }, auth=self.user.auth, expect_errors=True)
        assert_equals(rv.status_int, http.BAD_REQUEST)
        assert_in('Unable to list containers.', rv.body)

    def test_swift_remove_node_settings_owner(self):
        url = self.node_settings.owner.api_url_for('swift_deauthorize_node')
        ret = self.app.delete(url, auth=self.user.auth)
        result = self.Serializer().serialize_settings(node_settings=self.node_settings, current_user=self.user)
        assert_equal(result['nodeHasAuth'], False)

    def test_swift_remove_node_settings_unauthorized(self):
        url = self.node_settings.owner.api_url_for('swift_deauthorize_node')
        ret = self.app.delete(url, auth=None, expect_errors=True)

        assert_equal(ret.status_code, 401)

    def test_swift_get_node_settings_owner(self):
        self.node_settings.set_auth(self.external_account, self.user)
        self.node_settings.folder_id = 'bucket'
        self.node_settings.save()
        url = self.node_settings.owner.api_url_for('swift_get_config')
        res = self.app.get(url, auth=self.user.auth)

        result = res.json['result']
        assert_equal(result['nodeHasAuth'], True)
        assert_equal(result['userIsOwner'], True)
        assert_equal(result['folder']['path'], self.node_settings.folder_id)

    def test_swift_get_node_settings_unauthorized(self):
        url = self.node_settings.owner.api_url_for('swift_get_config')
        unauthorized = AuthUserFactory()
        ret = self.app.get(url, auth=unauthorized.auth, expect_errors=True)

        assert_equal(ret.status_code, 403)

    ## Overrides ##

    @mock.patch('addons.swift.models.get_container_names')
    def test_folder_list(self, mock_names):
        mock_names.return_value = ['bucket1', 'bucket2']
        super(TestSwiftViews, self).test_folder_list()

    @mock.patch('addons.swift.models.container_exists')
    def test_set_config(self, mock_exists):
        mock_exists.return_value = True
        self.node_settings.set_auth(self.external_account, self.user)
        url = self.project.api_url_for('{0}_set_config'.format(self.ADDON_SHORT_NAME))
        res = self.app.put_json(url, {
            'selected': self.folder
        }, auth=self.user.auth)
        assert_equal(res.status_code, http.OK)
        self.project.reload()
        self.node_settings.reload()
        assert_equal(
            self.project.logs.latest().action,
            '{0}_bucket_linked'.format(self.ADDON_SHORT_NAME)
        )
        assert_equal(res.json['result']['folder']['name'], self.node_settings.folder_name)


class TestCreateContainer(SwiftAddonTestCase, OsfTestCase):

    def setUp(self):

        super(TestCreateContainer, self).setUp()

        self.user = AuthUserFactory()
        self.consolidated_auth = Auth(user=self.user)
        self.auth = self.user.auth
        self.project = ProjectFactory(creator=self.user)

        self.project.add_addon('swift', auth=self.consolidated_auth)
        self.project.creator.add_addon('swift')

        self.user_settings = self.user.get_addon('swift')
        self.user_settings.access_key = 'We-Will-Rock-You'
        self.user_settings.secret_key = 'Idontknowanyqueensongs'
        self.user_settings.save()

        self.node_settings = self.project.get_addon('swift')
        self.node_settings.container = 'Sheer-Heart-Attack'
        self.node_settings.user_settings = self.project.creator.get_addon('swift')

        self.node_settings.save()

    def test_bad_names(self):
        assert_false(validate_container_name(''))
        assert_false(validate_container_name('a' * 257))
        assert_false(validate_container_name('a/b'))
        assert_false(validate_container_name('a/'))
        assert_false(validate_container_name('/a'))

    def test_names(self):
        assert_true(validate_container_name('a'))
        assert_true(validate_container_name('1'))
        assert_true(validate_container_name('can have whitespaces'))
        assert_true(validate_container_name('imagoodname'))
        assert_true(validate_container_name('still.passing'))
        assert_true(validate_container_name('can-have-dashes'))
        assert_true(validate_container_name('kinda.name.spaced'))
        assert_true(validate_container_name('a-o.valid'))
        assert_true(validate_container_name('11.12.m'))
        assert_true(validate_container_name('a--------a'))
        assert_true(validate_container_name('a' * 256))


    @mock.patch('addons.swift.views.utils.create_container')
    @mock.patch('addons.swift.views.utils.get_container_names')
    def test_create_container_pass(self, mock_names, mock_make):
        mock_make.return_value = True
        mock_names.return_value = [
            'butintheend',
            'it',
            'doesntevenmatter'
        ]
        url = self.project.api_url_for('swift_create_container')
        ret = self.app.post_json(
            url,
            {
                'container_name': 'doesntevenmatter'
            },
            auth=self.user.auth
        )

        assert_equal(ret.status_int, http.OK)
        assert_equal(ret.json, {})

    @mock.patch('addons.swift.views.utils.create_container')
    def test_create_container_fail(self, mock_make):
        error = swift_exceptions.ClientException('This should work',
                                                 http_status=418,
                                                 http_reason='because Im a test')
        mock_make.side_effect = error

        url = "/api/v1/project/{0}/swift/newcontainer/".format(self.project._id)
        ret = self.app.post_json(url, {'container_name': 'doesntevenmatter'}, auth=self.user.auth, expect_errors=True)

        assert_equals(ret.body, '{"message": "This should work", "title": "Problem creating container \'doesntevenmatter\'"}')

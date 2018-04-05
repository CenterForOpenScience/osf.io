# -*- coding: utf-8 -*-
import httplib as http

from boto.exception import S3ResponseError
import mock
from nose.tools import (assert_equal, assert_equals,
    assert_true, assert_in, assert_false)
import pytest

from framework.auth import Auth
from tests.base import OsfTestCase, get_default_metaschema
from osf_tests.factories import ProjectFactory, AuthUserFactory

from addons.base.tests.views import (
    OAuthAddonConfigViewsTestCaseMixin
)
from addons.s3compat.tests.utils import S3CompatAddonTestCase
from addons.s3compat.utils import validate_bucket_name
import addons.s3compat.settings as s3compat_settings
from website.util import api_url_for

pytestmark = pytest.mark.django_db

class TestS3CompatViews(S3CompatAddonTestCase, OAuthAddonConfigViewsTestCaseMixin, OsfTestCase):
    def setUp(self):
        self.mock_can_list = mock.patch('addons.s3compat.views.utils.can_list')
        self.mock_can_list.return_value = True
        self.mock_can_list.start()
        self.mock_uid = mock.patch('addons.s3compat.views.utils.get_user_info')
        self.mock_uid.return_value = {'id': '1234567890', 'display_name': 's3compat.user'}
        self.mock_uid.start()
        self.mock_exists = mock.patch('addons.s3compat.views.utils.bucket_exists')
        self.mock_exists.return_value = True
        self.mock_exists.start()
        super(TestS3CompatViews, self).setUp()

    def tearDown(self):
        self.mock_can_list.stop()
        self.mock_uid.stop()
        self.mock_exists.stop()
        super(TestS3CompatViews, self).tearDown()

    def test_s3compat_settings_input_empty_keys(self):
        url = self.project.api_url_for('s3compat_add_user_account')
        rv = self.app.post_json(url, {
            'host': '',
            'access_key': '',
            'secret_key': ''
        }, auth=self.user.auth, expect_errors=True)
        assert_equals(rv.status_int, http.BAD_REQUEST)
        assert_in('All the fields above are required.', rv.body)

    def test_s3compat_settings_input_empty_host(self):
        url = self.project.api_url_for('s3compat_add_user_account')
        rv = self.app.post_json(url, {
            'host': '',
            'access_key': 'Non-empty-access-key',
            'secret_key': 'Non-empty-secret-key'
        }, auth=self.user.auth, expect_errors=True)
        assert_equals(rv.status_int, http.BAD_REQUEST)
        assert_in('All the fields above are required.', rv.body)

    def test_s3compat_settings_input_empty_access_key(self):
        url = self.project.api_url_for('s3compat_add_user_account')
        rv = self.app.post_json(url, {
            'host': 'Non-empty-host',
            'access_key': '',
            'secret_key': 'Non-empty-secret-key'
        }, auth=self.user.auth, expect_errors=True)
        assert_equals(rv.status_int, http.BAD_REQUEST)
        assert_in('All the fields above are required.', rv.body)

    def test_s3compat_settings_input_empty_secret_key(self):
        url = self.project.api_url_for('s3compat_add_user_account')
        rv = self.app.post_json(url, {
            'host': 'Non-empty-host',
            'access_key': 'Non-empty-access-key',
            'secret_key': ''
        }, auth=self.user.auth, expect_errors=True)
        assert_equals(rv.status_int, http.BAD_REQUEST)
        assert_in('All the fields above are required.', rv.body)

    def test_s3compat_settings_input_unknown_host(self):
        url = self.project.api_url_for('s3compat_add_user_account')
        rv = self.app.post_json(url, {
            'host': 'Non-empty-host',
            'access_key': 'Non-empty-access-key',
            'secret_key': 'Non-empty-secret-key'
        }, auth=self.user.auth, expect_errors=True)
        assert_equals(rv.status_int, http.BAD_REQUEST)
        assert_in('The host is not available.', rv.body)

    def test_s3compat_set_bucket_no_settings(self):
        user = AuthUserFactory()
        self.project.add_contributor(user, save=True)
        url = self.project.api_url_for('s3compat_set_config')
        res = self.app.put_json(
            url, {'s3compat_bucket': 'hammertofall'}, auth=user.auth,
            expect_errors=True
        )
        assert_equal(res.status_code, http.BAD_REQUEST)

    def test_s3compat_set_bucket_no_auth(self):

        user = AuthUserFactory()
        user.add_addon('s3compat')
        self.project.add_contributor(user, save=True)
        url = self.project.api_url_for('s3compat_set_config')
        res = self.app.put_json(
            url, {'s3compat_bucket': 'hammertofall'}, auth=user.auth,
            expect_errors=True
        )
        assert_equal(res.status_code, http.FORBIDDEN)

    def test_s3compat_set_bucket_registered(self):
        registration = self.project.register_node(
            get_default_metaschema(), Auth(self.user), '', ''
        )

        url = registration.api_url_for('s3compat_set_config')
        res = self.app.put_json(
            url, {'s3compat_bucket': 'hammertofall'}, auth=self.user.auth,
            expect_errors=True,
        )

        assert_equal(res.status_code, http.BAD_REQUEST)

    @mock.patch('addons.s3compat.views.utils.can_list', return_value=False)
    def test_user_settings_cant_list(self, mock_can_list):
        url = api_url_for('s3compat_add_user_account')
        rv = self.app.post_json(url, {
            'host': s3compat_settings.AVAILABLE_SERVICES[0]['host'],
            'access_key': 'aldkjf',
            'secret_key': 'las'
        }, auth=self.user.auth, expect_errors=True)
        assert_equals(rv.status_int, http.BAD_REQUEST)
        assert_in('Unable to list buckets.', rv.body)

    def test_s3compat_remove_node_settings_owner(self):
        url = self.node_settings.owner.api_url_for('s3compat_deauthorize_node')
        self.app.delete(url, auth=self.user.auth)
        result = self.Serializer().serialize_settings(node_settings=self.node_settings, current_user=self.user)
        assert_equal(result['nodeHasAuth'], False)

    def test_s3compat_remove_node_settings_unauthorized(self):
        url = self.node_settings.owner.api_url_for('s3compat_deauthorize_node')
        ret = self.app.delete(url, auth=None, expect_errors=True)

        assert_equal(ret.status_code, 401)

    def test_s3compat_get_node_settings_owner(self):
        self.node_settings.set_auth(self.external_account, self.user)
        self.node_settings.folder_id = 'bucket'
        self.node_settings.save()
        url = self.node_settings.owner.api_url_for('s3compat_get_config')
        res = self.app.get(url, auth=self.user.auth)

        result = res.json['result']
        assert_equal(result['nodeHasAuth'], True)
        assert_equal(result['userIsOwner'], True)
        assert_equal(result['folder']['path'], self.node_settings.folder_id)

    def test_s3compat_get_node_settings_unauthorized(self):
        url = self.node_settings.owner.api_url_for('s3compat_get_config')
        unauthorized = AuthUserFactory()
        ret = self.app.get(url, auth=unauthorized.auth, expect_errors=True)

        assert_equal(ret.status_code, 403)

    ## Overrides ##

    @mock.patch('addons.s3compat.models.get_bucket_names')
    def test_folder_list(self, mock_names):
        mock_names.return_value = ['bucket1', 'bucket2']
        super(TestS3CompatViews, self).test_folder_list()

    @mock.patch('addons.s3compat.models.bucket_exists')
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


class TestCreateBucket(S3CompatAddonTestCase, OsfTestCase):

    def setUp(self):

        super(TestCreateBucket, self).setUp()

        self.user = AuthUserFactory()
        self.consolidated_auth = Auth(user=self.user)
        self.auth = self.user.auth
        self.project = ProjectFactory(creator=self.user)

        self.project.add_addon('s3compat', auth=self.consolidated_auth)
        self.project.creator.add_addon('s3compat')

        self.user_settings = self.user.get_addon('s3compat')
        self.user_settings.access_key = 'We-Will-Rock-You'
        self.user_settings.secret_key = 'Idontknowanyqueensongs'
        self.user_settings.save()

        self.node_settings = self.project.get_addon('s3compat')
        self.node_settings.bucket = 'Sheer-Heart-Attack'
        self.node_settings.user_settings = self.project.creator.get_addon('s3compat')

        self.node_settings.save()

    def test_bad_names(self):
        assert_false(validate_bucket_name(''))
        assert_false(validate_bucket_name('no'))
        assert_false(validate_bucket_name('a' * 64))
        assert_false(validate_bucket_name(' leadingspace'))
        assert_false(validate_bucket_name('trailingspace '))
        assert_false(validate_bucket_name('bogus naMe'))
        assert_false(validate_bucket_name('.cantstartwithp'))
        assert_false(validate_bucket_name('or.endwith.'))
        assert_false(validate_bucket_name('..nodoubles'))
        assert_false(validate_bucket_name('no_unders_in'))
        assert_false(validate_bucket_name('-leadinghyphen'))
        assert_false(validate_bucket_name('trailinghyphen-'))
        assert_false(validate_bucket_name('Mixedcase'))
        assert_false(validate_bucket_name('empty..label'))
        assert_false(validate_bucket_name('label-.trailinghyphen'))
        assert_false(validate_bucket_name('label.-leadinghyphen'))
        assert_false(validate_bucket_name('8.8.8.8'))
        assert_false(validate_bucket_name('600.9000.0.28'))
        assert_false(validate_bucket_name('no_underscore'))
        assert_false(validate_bucket_name('_nounderscoreinfront'))
        assert_false(validate_bucket_name('no-underscore-in-back_'))
        assert_false(validate_bucket_name('no-underscore-in_the_middle_either'))

    def test_names(self):
        assert_true(validate_bucket_name('imagoodname'))
        assert_true(validate_bucket_name('still.passing'))
        assert_true(validate_bucket_name('can-have-dashes'))
        assert_true(validate_bucket_name('kinda.name.spaced'))
        assert_true(validate_bucket_name('a-o.valid'))
        assert_true(validate_bucket_name('11.12.m'))
        assert_true(validate_bucket_name('a--------a'))
        assert_true(validate_bucket_name('a' * 63))

    @mock.patch('addons.s3compat.views.utils.create_bucket')
    @mock.patch('addons.s3compat.views.utils.get_bucket_names')
    def test_create_bucket_pass(self, mock_names, mock_make):
        mock_make.return_value = True
        mock_names.return_value = [
            'butintheend',
            'it',
            'doesntevenmatter'
        ]
        url = self.project.api_url_for('s3compat_create_bucket')
        ret = self.app.post_json(
            url,
            {
                'bucket_name': 'doesntevenmatter'
            },
            auth=self.user.auth
        )

        assert_equal(ret.status_int, http.OK)
        assert_equal(ret.json, {})

    @mock.patch('addons.s3compat.views.utils.create_bucket')
    def test_create_bucket_fail(self, mock_make):
        error = S3ResponseError(418, 'because Im a test')
        error.message = 'This should work'
        mock_make.side_effect = error

        url = "/api/v1/project/{0}/s3compat/newbucket/".format(self.project._id)
        ret = self.app.post_json(url, {'bucket_name': 'doesntevenmatter'}, auth=self.user.auth, expect_errors=True)

        assert_equals(ret.body, '{"message": "This should work", "title": "Problem connecting to S3 Compatible Storage"}')

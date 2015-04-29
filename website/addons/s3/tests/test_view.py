import mock
from nose.tools import *  # noqa

import httplib as http
from boto.exception import S3ResponseError

from framework.auth import Auth
from tests.base import OsfTestCase
from tests.factories import ProjectFactory, AuthUserFactory

from website.addons.s3.utils import validate_bucket_name
from website.util import api_url_for

from utils import create_mock_wrapper

from faker import Faker
fake = Faker()


class MockS3Bucket(object):

    def __init__(self, **kwargs):
        for k, v in kwargs.iteritems():
            setattr(self, k, v)

class TestS3ViewsConfig(OsfTestCase):

    def setUp(self):

        super(TestS3ViewsConfig, self).setUp()

        self.user = AuthUserFactory()
        self.consolidated_auth = Auth(user=self.user)
        self.auth = ('test', self.user.api_keys[0]._primary_key)
        self.project = ProjectFactory(creator=self.user)

        self.project.add_addon('s3', auth=self.consolidated_auth)
        self.project.creator.add_addon('s3')

        self.user_settings = self.user.get_addon('s3')
        self.user_settings.access_key = 'We-Will-Rock-You'
        self.user_settings.secret_key = 'Idontknowanyqueensongs'
        self.user_settings.save()

        self.node_settings = self.project.get_addon('s3')
        self.node_settings.bucket = 'Sheer-Heart-Attack'
        self.node_settings.user_settings = self.project.creator.get_addon('s3')

        self.node_settings.save()
        self.node_url = '/api/v1/project/{0}/'.format(self.project._id)

    @mock.patch('website.addons.s3.api.has_access')
    @mock.patch('website.addons.s3.views.config.does_bucket_exist')
    @mock.patch('website.addons.s3.views.config.adjust_cors')
    def test_s3_settings_no_bucket(self, mock_cors, mock_does_bucket_exist, mock_has_access):
        mock_has_access.return_value = True
        mock_does_bucket_exist.return_value = False
        mock_cors.return_value = True
        url = self.project.api_url + 's3/settings/'
        rv = self.app.post_json(url, {}, expect_errors=True, auth=self.user.auth)
        assert_true('trouble' in rv.body)

    @mock.patch('website.addons.s3.api.has_access')
    @mock.patch('website.addons.s3.views.config.does_bucket_exist')
    @mock.patch('website.addons.s3.views.config.adjust_cors')
    @mock.patch('website.addons.s3.utils.get_bucket_drop_down')
    def test_s3_set_bucket(self, mock_cors, mock_exist, mock_dropdown, mock_has_access):
        mock_has_access.return_value = True
        mock_cors.return_value = True
        mock_exist.return_value = True
        mock_dropdown.return_value = ['mybucket']
        url = self.project.api_url_for('s3_node_settings')
        self.app.post_json(
            url, {'s3_bucket': 'hammertofall'}, auth=self.user.auth,
        )

        self.project.reload()
        self.node_settings.reload()

        assert_equal(self.node_settings.bucket, 'hammertofall')
        assert_equal(self.project.logs[-1].action, 's3_bucket_linked')

    def test_s3_set_bucket_no_settings(self):

        user = AuthUserFactory()
        self.project.add_contributor(user, save=True)
        url = self.project.api_url + 's3/settings/'
        res = self.app.post_json(
            url, {'s3_bucket': 'hammertofall'}, auth=user.auth,
            expect_errors=True
        )
        assert_equal(res.status_code, http.BAD_REQUEST)
        
    def test_s3_set_bucket_no_auth(self):

        user = AuthUserFactory()
        user.add_addon('s3')
        self.project.add_contributor(user, save=True)
        url = self.project.api_url + 's3/settings/'
        res = self.app.post_json(
            url, {'s3_bucket': 'hammertofall'}, auth=user.auth,
            expect_errors=True
        )
        assert_equal(res.status_code, http.BAD_REQUEST)

    def test_s3_set_bucket_already_authed(self):

        user = AuthUserFactory()
        user.add_addon('s3')
        user_settings = user.get_addon('s3')
        user_settings.access_key = 'foo'
        user_settings.secret_key = 'bar'
        user_settings.save()
        self.project.add_contributor(user, save=True)
        url = self.project.api_url + 's3/settings/'
        res = self.app.post_json(
            url, {'s3_bucket': 'hammertofall'}, auth=user.auth,
            expect_errors=True
        )
        assert_equal(res.status_code, http.BAD_REQUEST)

    @mock.patch('website.addons.s3.api.S3Wrapper.from_addon')
    def test_s3_set_bucket_registered(self, mock_from_addon):

        mock_from_addon.return_value = create_mock_wrapper()

        registration = self.project.register_node(
            None, self.consolidated_auth, '', ''
        )

        url = registration.api_url + 's3/settings/'
        res = self.app.post_json(
            url, {'s3_bucket': 'hammertofall'}, auth=self.user.auth,
            expect_errors=True,
        )

        assert_equal(res.status_code, http.BAD_REQUEST)

    @mock.patch('website.addons.s3.views.config.has_access')
    @mock.patch('website.addons.s3.views.config.create_osf_user')
    def test_user_settings(self, mock_user, mock_access):
        mock_access.return_value = True
        mock_user.return_value = (
            'osf-user-12345',
            {
                'access_key_id': 'scout',
                'secret_access_key': 'ssshhhhhhhhh'
            }
        )
        url = '/api/v1/settings/s3/'
        self.app.post_json(
            url,
            {
                'access_key': 'scout',
                'secret_key': 'Atticus'
            },
            auth=self.user.auth
        )
        self.user_settings.reload()
        assert_equals(self.user_settings.access_key, 'scout')

    @mock.patch('website.addons.s3.model.AddonS3UserSettings.remove_iam_user')
    def test_s3_remove_user_settings(self, mock_access):
        mock_access.return_value = True
        self.user_settings.access_key = 'to-kill-a-mocking-bucket'
        self.user_settings.secret_key = 'itsasecret'
        self.user_settings.save()
        url = api_url_for('s3_remove_user_settings')
        self.app.delete(url, auth=self.user.auth)
        self.user_settings.reload()
        assert_equals(self.user_settings.access_key, None)
        assert_equals(self.user_settings.secret_key, None)
        assert_equals(mock_access.call_count, 1)

    @mock.patch('website.addons.s3.model.AddonS3UserSettings.remove_iam_user')
    def test_s3_remove_user_settings_none(self, mock_access):
        self.user_settings.access_key = None
        self.user_settings.secret_key = None
        self.user_settings.save()
        url = api_url_for('s3_remove_user_settings')
        self.app.delete(url, auth=self.user.auth)
        self.user_settings.reload()
        assert_equals(mock_access.call_count, 0)

    @mock.patch('website.addons.s3.views.config.has_access')
    def test_user_settings_no_auth(self, mock_access):
        mock_access.return_value = False
        url = '/api/v1/settings/s3/'
        rv = self.app.post_json(url, {}, auth=self.user.auth, expect_errors=True)
        assert_equals(rv.status_int, http.BAD_REQUEST)

    @mock.patch('website.addons.s3.api.has_access')
    @mock.patch('website.addons.s3.utils.get_bucket_drop_down')
    @mock.patch('website.addons.s3.views.config.has_access')
    @mock.patch('website.addons.s3.views.config.create_osf_user')
    def test_node_settings_no_user_settings(self, mock_user, mock_access, mock_dropdown, mock_is_valid):
        self.node_settings.user_settings = None
        self.node_settings.save()
        url = self.node_url + 's3/authorize/'

        mock_is_valid.return_value = True
        mock_access.return_value = True
        mock_user.return_value = (
            'osf-user-12345',
            {
                'access_key_id': 'scout',
                'secret_access_key': 'ssshhhhhhhhh'
            }
        )
        mock_dropdown.return_value = ['mybucket']
        self.app.post_json(url, {'access_key': 'scout', 'secret_key': 'ssshhhhhhhhh'}, auth=self.user.auth)
        self.user_settings.reload()
        assert_equals(self.user_settings.access_key, 'scout')

    @mock.patch('website.addons.s3.utils.get_bucket_list')
    def test_s3_bucket_list(self, mock_bucket_list):
        fake_buckets = [
            MockS3Bucket(name=fake.domain_word())
            for i in range(10)
        ]
        mock_bucket_list.return_value = fake_buckets
        url = self.node_settings.owner.api_url_for('s3_bucket_list')
        ret = self.app.get(url, auth=self.user.auth)

        assert_equals(ret.json, {'buckets': [bucket.name for bucket in fake_buckets]})

    @mock.patch('website.addons.s3.api.has_access')
    def test_s3_remove_node_settings_owner(self, mock_has_access):
        mock_has_access.return_value = True

        url = self.node_settings.owner.api_url_for('s3_remove_node_settings')
        ret = self.app.delete(url, auth=self.user.auth)

        assert_equal(ret.json['has_bucket'], False)
        assert_equal(ret.json['node_has_auth'], False)

    def test_s3_remove_node_settings_unauthorized(self):
        url = self.node_settings.owner.api_url_for('s3_remove_node_settings')
        ret = self.app.delete(url, auth=None, expect_errors=True)

        assert_equal(ret.status_code, 401)

    @mock.patch('website.addons.s3.api.has_access')
    def test_s3_get_node_settings_owner(self, mock_has_access):
        mock_has_access.return_value = True
        
        url = self.node_settings.owner.api_url_for('s3_get_node_settings')
        res = self.app.get(url, auth=self.user.auth)

        expected_bucket = self.node_settings.bucket
        expected_node_has_auth = True
        expected_user_is_owner = True
        result = res.json['result']
        assert_equal(result['bucket'], expected_bucket)
        assert_equal(result['node_has_auth'], expected_node_has_auth)
        assert_equal(result['user_is_owner'], expected_user_is_owner)

    def test_s3_get_node_settings_not_owner(self):
        url = self.node_settings.owner.api_url_for('s3_get_node_settings')
        non_owner = AuthUserFactory()
        self.project.add_contributor(non_owner, save=True, permissions=['write'])
        res = self.app.get(url, auth=non_owner.auth)

        expected_bucket = self.node_settings.bucket
        expected_node_has_auth = True
        expected_user_is_owner = False
        result = res.json['result']
        assert_equal(result['bucket'], expected_bucket)
        assert_equal(result['node_has_auth'], expected_node_has_auth)
        assert_equal(result['user_is_owner'], expected_user_is_owner)

    def test_s3_get_node_settings_unauthorized(self):
        url = self.node_settings.owner.api_url_for('s3_get_node_settings')
        unauthorized = AuthUserFactory()
        ret = self.app.get(url, auth=unauthorized.auth, expect_errors=True)

        assert_equal(ret.status_code, 403)

    @mock.patch('website.addons.s3.api.has_access')
    @mock.patch('website.addons.s3.views.config.add_s3_auth')
    def test_s3_authorize_node_valid(self, mock_add, mock_has_access):
        mock_has_access.return_value = True
        mock_add.return_value = True
        url = self.project.api_url_for('s3_authorize_node')
        cred = {
            'access_key': fake.password(),
            'secret_key': fake.password(),
        }
        res = self.app.post_json(url, cred, auth=self.user.auth)
        assert_equal(res.json['node_has_auth'], True)

    def test_s3_authorize_node_invalid(self):
        url = self.project.api_url_for('s3_authorize_node')
        cred = {
            'access_key': fake.password(),
        }
        res = self.app.post_json(url, cred, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)

    @mock.patch('website.addons.s3.views.config.add_s3_auth')
    def test_s3_authorize_node_malformed(self, mock_add):
        mock_add.return_value = False
        url = self.project.api_url_for('s3_authorize_node')
        cred = {
            'access_key': fake.password(),
            'secret_key': fake.password(),
        }
        res = self.app.post_json(url, cred, auth=self.user.auth, expect_errors=True)
        assert_equal(res.json['message'], 'Incorrect credentials')
        assert_equal(res.status_code, 400)

    @mock.patch('website.addons.s3.views.config.add_s3_auth')
    def test_s3_authorize_node_unauthorized(self, mock_add):
        mock_add.return_value = True
        url = self.project.api_url_for('s3_authorize_node')
        cred = {
            'access_key': fake.password(),
            'secret_key': fake.password(),
        }
        unauthorized = AuthUserFactory()
        res = self.app.post_json(url, cred, auth=unauthorized.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

    @mock.patch('website.addons.s3.views.config.add_s3_auth')
    def test_s3_authorize_user_valid(self, mock_add):
        mock_add.return_value = True
        url = self.project.api_url_for('s3_authorize_user')
        cred = {
            'access_key': fake.password(),
            'secret_key': fake.password(),
        }
        res = self.app.post_json(url, cred, auth=self.user.auth)
        assert_equal(res.json, {})

    def test_s3_authorize_user_invalid(self):
        url = self.project.api_url_for('s3_authorize_user')
        cred = {
            'access_key': fake.password(),
        }
        res = self.app.post_json(url, cred, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 400)

    @mock.patch('website.addons.s3.views.config.add_s3_auth')
    def test_s3_authorize_user_malformed(self, mock_add):
        mock_add.return_value = False
        url = self.project.api_url_for('s3_authorize_user')
        cred = {
            'access_key': fake.password(),
            'secret_key': fake.password(),
        }
        res = self.app.post_json(url, cred, auth=self.user.auth, expect_errors=True)
        assert_equal(res.json['message'], 'Incorrect credentials')
        assert_equal(res.status_code, 400)

    @mock.patch('website.addons.s3.api.has_access')
    def test_s3_node_import_auth_authorized(self, mock_has_access):
        mock_has_access.return_value = True
        url = self.project.api_url_for('s3_node_import_auth')
        self.node_settings.deauthorize(auth=None, save=True)
        res = self.app.post(url, auth=self.user.auth)
        assert_equal(res.json['node_has_auth'], True)
        assert_equal(res.json['user_is_owner'], True)

    def test_s3_node_import_auth_unauthorized(self):
        url = self.project.api_url_for('s3_node_import_auth')
        self.node_settings.deauthorize(auth=None, save=True)
        unauthorized = AuthUserFactory()
        res = self.app.post(url, auth=unauthorized.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

class TestCreateBucket(OsfTestCase):

    def setUp(self):

        super(TestCreateBucket, self).setUp()

        self.user = AuthUserFactory()
        self.consolidated_auth = Auth(user=self.user)
        self.auth = ('test', self.user.api_keys[0]._primary_key)
        self.project = ProjectFactory(creator=self.user)

        self.project.add_addon('s3', auth=self.consolidated_auth)
        self.project.creator.add_addon('s3')

        self.user_settings = self.user.get_addon('s3')
        self.user_settings.access_key = 'We-Will-Rock-You'
        self.user_settings.secret_key = 'Idontknowanyqueensongs'
        self.user_settings.save()

        self.node_settings = self.project.get_addon('s3')
        self.node_settings.bucket = 'Sheer-Heart-Attack'
        self.node_settings.user_settings = self.project.creator.get_addon('s3')

        self.node_settings.save()

    def test_bad_names(self):
        assert_false(validate_bucket_name('bogus naMe'))
        assert_false(validate_bucket_name(''))
        assert_false(validate_bucket_name('no'))
        assert_false(validate_bucket_name('.cantstartwithp'))
        assert_false(validate_bucket_name('or.endwith.'))
        assert_false(validate_bucket_name('..nodoubles'))
        assert_false(validate_bucket_name('no_unders_in'))

    def test_names(self):
        assert_true(validate_bucket_name('imagoodname'))
        assert_true(validate_bucket_name('still.passing'))
        assert_true(validate_bucket_name('can-have-dashes'))
        assert_true(validate_bucket_name('kinda.name.spaced'))

    
    @mock.patch('website.addons.s3.views.crud.create_bucket')
    @mock.patch('website.addons.s3.utils.get_bucket_drop_down')
    def test_create_bucket_pass(self, mock_make, mock_dropdown):
        mock_make.return_value = True
        mock_dropdown.return_value = ['mybucket']
        url = self.project.api_url_for('create_new_bucket')
        ret = self.app.post_json(url, {'bucket_name': 'doesntevenmatter'}, auth=self.user.auth)

        assert_equals(ret.status_int, http.OK)

    @mock.patch('website.addons.s3.views.crud.create_bucket')
    def test_create_bucket_fail(self, mock_make):
        error = S3ResponseError(418, 'because Im a test')
        error.message = 'This should work'
        mock_make.side_effect = error

        url = "/api/v1/project/{0}/s3/newbucket/".format(self.project._id)
        ret = self.app.post_json(url, {'bucket_name': 'doesntevenmatter'}, auth=self.user.auth, expect_errors=True)

        assert_equals(ret.body, '{"message": "This should work", "title": "Problem connecting to S3"}')

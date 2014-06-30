from nose.tools import *
import mock
from boto.s3.connection import *

from tests.base import OsfTestCase
from tests.factories import UserFactory, ProjectFactory

from framework.auth import Auth
from website.addons.s3.model import AddonS3NodeSettings, AddonS3UserSettings


class TestCallbacks(OsfTestCase):

    def setUp(self):

        super(TestCallbacks, self).setUp()

        self.project = ProjectFactory.build()
        self.consolidated_auth = Auth(user=self.project.creator)
        self.non_authenticator = UserFactory()
        self.project.add_contributor(
            contributor=self.non_authenticator,
            auth=Auth(self.project.creator),
        )
        self.project.save()

        self.project.add_addon('s3', auth=self.consolidated_auth)
        self.project.creator.add_addon('s3')
        self.node_settings = self.project.get_addon('s3')
        self.user_settings = self.project.creator.get_addon('s3')
        self.user_settings.access_key = 'We-Will-Rock-You'
        self.user_settings.secret_key = 'Idontknowanyqueensongs'
        self.node_settings.bucket = 'Sheer-Heart-Attack'
        self.node_settings.user_settings = self.user_settings
        self.node_settings.save()

    @mock.patch('website.addons.s3.model.get_bucket_drop_down')
    def test_node_settings_empty_bucket(self, mock_drop):
        mock_drop.return_value = ''
        s3 = AddonS3NodeSettings(owner=self.project)
        assert_equals(s3.to_json(self.project.creator)['has_bucket'], 0)

    @mock.patch('website.addons.s3.model.get_bucket_drop_down')
    def test_node_settings_full_bucket(self, mock_drop):
        mock_drop.return_value = ''
        s3 = AddonS3NodeSettings(owner=self.project)
        s3.bucket = 'bucket'
        assert_equals(s3.to_json(self.project.creator)['has_bucket'], 1)

    @mock.patch('website.addons.s3.model.get_bucket_drop_down')
    def test_node_settings_user_auth(self, mock_drop):
        mock_drop.return_value = ''
        s3 = AddonS3NodeSettings(owner=self.project)
        assert_equals(s3.to_json(self.project.creator)['user_has_auth'], 1)

    @mock.patch('website.addons.s3.model.get_bucket_drop_down')
    def test_node_settings_moar_use(self, mock_drop):
        mock_drop.return_value = ''
        assert_equals(self.node_settings.to_json(
            self.project.creator)['user_has_auth'], 1)

    @mock.patch('website.addons.s3.model.get_bucket_drop_down')
    def test_node_settings_no_contributor_user_settings(self, mock_drop):
        mock_drop.return_value = ''
        user2 = UserFactory()
        self.project.add_contributor(user2)
        assert_false(
            self.node_settings.to_json(user2)['user_has_auth']
        )

    def test_user_settings(self):
        s3 = AddonS3UserSettings(owner=self.project)
        s3.access_key = "Sherlock"
        s3.secret_key = "lives"
        assert_equals(s3.to_json(self.project.creator)['has_auth'], 1)

    def test_after_fork_authenticator(self):
        fork = ProjectFactory()
        clone, message = self.node_settings.after_fork(self.project,
                                                       fork, self.project.creator)
        assert_equal(self.node_settings.user_settings, clone.user_settings)

    def test_after_fork_not_authenticator(self):
        fork = ProjectFactory()
        clone, message = self.node_settings.after_fork(
            self.project, fork, self.non_authenticator,
        )
        assert_equal(clone.user_settings, None)

    @mock.patch('website.addons.s3.utils.get_bucket_list')
    def test_drop_down_disabled(self, mock_drop):
        bucket = mock.create_autospec(Bucket)
        bucket.name = 'Atticus'
        mock_drop.return_value = [bucket]
        drop_list = self.node_settings.to_json(self.project.creator)['bucket_list']
        assert_true('Atticus' in drop_list)

    @mock.patch('website.addons.s3.model.serialize_bucket')
    @mock.patch('website.addons.s3.model.S3Wrapper.from_addon')
    def test_registration(self, mock_wrapper, mock_bucket):
        mock_wrapper.return_value = None
        mock_bucket.return_value = {'Not None': 'None'}
        fork = ProjectFactory()
        clone, message = self.node_settings.after_register(
            self.project, fork, self.project.creator,
        )
        assert_true(clone.is_registration)

    def test_after_remove_contributor(self):
        self.node_settings.after_remove_contributor(
            self.project, self.project.creator
        )
        assert_equal(self.node_settings.user_settings, None)

    @mock.patch('website.addons.s3.model.serialize_bucket')
    @mock.patch('website.addons.s3.model.S3Wrapper.from_addon')
    def test_registration_settings(self, mock_wrapper, mock_bucket):
        mock_wrapper.return_value = None
        mock_bucket.return_value = {'Not None': 'None'}
        fork = ProjectFactory()
        clone, message = self.node_settings.after_register(
            self.project, fork, self.project.creator,
        )
        assert_true(clone.user_settings)

    def test_before_register_no_settings(self):
        self.node_settings.user_settings = None
        message = self.node_settings.before_register(self.project, self.project.creator)
        assert_false(message)

    def test_before_register_no_auth(self):
        self.node_settings.user_settings.access_key = None
        message = self.node_settings.before_register(self.project, self.project.creator)
        assert_false(message)

    def test_before_register_settings_and_auth(self):
        message = self.node_settings.before_register(self.project, self.project.creator)
        assert_true(message)

    def test_after_delete(self):
        self.project.remove_node(Auth(user=self.project.creator))
        # Ensure that changes to node settings have been saved
        self.node_settings.reload()
        assert_true(self.node_settings.user_settings is None)
        assert_true(self.node_settings.bucket is None)

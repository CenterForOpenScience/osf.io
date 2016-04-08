from nose.tools import *  # noqa
import mock
from boto.s3.connection import *  # noqa

from tests.base import OsfTestCase, get_default_metaschema
from tests.factories import UserFactory, ProjectFactory

from framework.auth import Auth
from website.addons.s3.model import AddonS3NodeSettings, AddonS3UserSettings


class TestNodeSettings(OsfTestCase):
    def setUp(self):
        super(TestNodeSettings, self).setUp()
        self.user = UserFactory()
        self.project = ProjectFactory(creator=self.user)

        self.user.add_addon('s3')
        self.project.add_addon('s3', auth=Auth(self.user))

        self.user_settings = self.user.get_addon('s3')
        self.node_settings = self.project.get_addon('s3')

        self.user_settings.access_key = 'We-Will-Rock-You'
        self.user_settings.secret_key = 'Idontknowanyqueensongs'
        self.user_settings.save()

        self.node_settings.bucket = 'Sheer-Heart-Attack'
        self.node_settings.user_settings = self.user_settings
        self.node_settings.save()

    def test_complete_true(self):
        assert_true(self.node_settings.has_auth)
        assert_true(self.node_settings.complete)

    def test_complete_false(self):
        self.node_settings.bucket = None

        assert_true(self.node_settings.has_auth)
        assert_false(self.node_settings.complete)

    def test_complete_auth_false(self):
        self.node_settings.user_settings = None

        assert_false(self.node_settings.has_auth)
        assert_false(self.node_settings.complete)


class TestCallbacks(OsfTestCase):

    def setUp(self):

        super(TestCallbacks, self).setUp()

        self.project = ProjectFactory.create()
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

    @mock.patch('website.addons.s3.model.AddonS3UserSettings.is_valid')
    def test_node_settings_empty_bucket(self, mock_is_valid):
        mock_is_valid.return_value = True
        s3 = AddonS3NodeSettings(owner=self.project)
        assert_equals(s3.to_json(self.project.creator)['has_bucket'], 0)

    @mock.patch('website.addons.s3.model.AddonS3UserSettings.is_valid')
    def test_node_settings_full_bucket(self, mock_is_valid):
        mock_is_valid.return_value = True
        s3 = AddonS3NodeSettings(owner=self.project)
        s3.bucket = 'bucket'
        assert_equals(s3.to_json(self.project.creator)['has_bucket'], 1)

    @mock.patch('website.addons.s3.model.AddonS3UserSettings.is_valid')
    def test_node_settings_user_auth(self, mock_is_valid):
        mock_is_valid.return_value = True
        s3 = AddonS3NodeSettings(owner=self.project)
        assert_equals(s3.to_json(self.project.creator)['user_has_auth'], 1)

    @mock.patch('website.addons.s3.model.AddonS3UserSettings.is_valid')
    def test_node_settings_moar_use(self, mock_is_valid):
        mock_is_valid.return_value = True
        assert_equals(self.node_settings.to_json(
            self.project.creator)['user_has_auth'], 1)

    @mock.patch('website.addons.s3.model.AddonS3UserSettings.is_valid')
    def test_node_settings_no_contributor_user_settings(self, mock_is_valid):
        mock_is_valid.return_value = True
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

    def test_is_valid_none_none(self):
        self.user_settings.access_key = None
        self.user_settings.secret_key = None
        assert_false(self.user_settings.is_valid)

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

    def test_after_remove_contributor_self(self):
        message = self.node_settings.after_remove_contributor(
            self.project, self.project.creator, self.consolidated_auth
        )
        assert_equal(self.node_settings.user_settings, None)
        assert_true(message)
        assert_not_in("You can re-authenticate", message)

    def test_after_remove_contributor_not_self(self):
        auth = Auth(user=self.non_authenticator)
        message = self.node_settings.after_remove_contributor(
            self.project, self.project.creator, auth
        )
        assert_equal(self.node_settings.user_settings, None)
        assert_true(message)
        assert_in("You can re-authenticate", message)

    def test_registration_settings(self):
        registration = ProjectFactory()
        clone, message = self.node_settings.after_register(
            self.project, registration, self.project.creator,
        )
        assert_is_none(clone)

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

    @mock.patch('website.archiver.tasks.archive')
    def test_does_not_get_copied_to_registrations(self, mock_archive):
        registration = self.project.register_node(
            schema=get_default_metaschema(),
            auth=Auth(user=self.project.creator),
            data='hodor',
        )
        assert_false(registration.has_addon('s3'))

from nose.tools import *  # noqa
import mock

from tests.base import get_default_metaschema
from tests.factories import UserFactory, ProjectFactory
from framework.auth.decorators import Auth
from framework.exceptions import PermissionsError

from website.addons.dataverse.model import AddonDataverseNodeSettings
from website.addons.dataverse.tests.utils import DataverseAddonTestCase
from website.addons.dataverse.tests.utils import create_external_account


class TestDataverseUserSettings(DataverseAddonTestCase):
    """Tests were modified from Mendeley. None of this functionality is
    currently Dataverse specific."""

    def _prep_auth_case(self):
        self.node = ProjectFactory()
        self.user = self.node.creator

        self.external_account = create_external_account()

        self.user.external_accounts.append(self.external_account)
        self.user.save()

        self.user_settings = self.user.get_or_add_addon('mendeley')

    def test_grant_auth_access_no_metadata(self):
        self._prep_auth_case()

        self.user_settings.grant_oauth_access(
            node=self.node,
            external_account=self.external_account,
        )
        self.user_settings.save()

        assert_equal(
            self.user_settings.oauth_grants,
            {self.node._id: {self.external_account._id: {}}},
        )

    def test_verify_oauth_access_no_metadata(self):
        self._prep_auth_case()

        self.user_settings.grant_oauth_access(
            node=self.node,
            external_account=self.external_account,
        )
        self.user_settings.save()

        assert_true(
            self.user_settings.verify_oauth_access(
                node=self.node,
                external_account=self.external_account
            )
        )

        assert_false(
            self.user_settings.verify_oauth_access(
                node=self.node,
                external_account=create_external_account()
            )
        )

class TestDataverseNodeSettings(DataverseAddonTestCase):

    def test_fields(self):
        node_settings = AddonDataverseNodeSettings(user_settings=self.user_settings)
        node_settings.save()
        assert_true(node_settings.user_settings)
        assert_equal(node_settings.user_settings.owner, self.user)
        assert_true(hasattr(node_settings, 'dataverse'))
        assert_true(hasattr(node_settings, 'dataverse_alias'))
        assert_true(hasattr(node_settings, 'dataset'))
        assert_true(hasattr(node_settings, 'dataset_doi'))

    def test_defaults(self):
        node_settings = AddonDataverseNodeSettings(user_settings=self.user_settings)
        node_settings.save()
        assert_is_none(node_settings.dataverse)
        assert_is_none(node_settings.dataverse_alias)
        assert_is_none(node_settings.dataset)
        assert_is_none(node_settings.dataset_doi)

    def test_has_auth(self):
        # No auth by default
        assert_false(self.node_settings.has_auth)

        # Append an external account
        external_account = create_external_account()
        self.user.external_accounts.append(external_account)
        self.node_settings.set_auth(external_account, self.user)
        assert_true(self.node_settings.has_auth)

        # Node settings configuration should have no effect
        self.node_settings.dataset_doi = None
        assert_true(self.node_settings.has_auth)

    def test_has_auth_false(self):
        # No auth by default
        assert_false(self.node_settings.has_auth)

        # both external_account and user_settings must be set to have auth
        external_account = create_external_account()
        self.node_settings.external_account = external_account
        assert_false(self.node_settings.has_auth)

        self.node_settings.external_account = None
        self.node_settings.user_settings = self.user_settings
        assert_false(self.node_settings.has_auth)

        # set_auth must be called to have auth
        self.node_settings.external_account = external_account
        self.node_settings.user_settings = self.user_settings
        assert_false(self.node_settings.has_auth)

    @mock.patch('website.addons.dataverse.model.AddonDataverseNodeSettings.deauthorize')
    def test_delete(self, mock_deauth):

        num_old_logs = len(self.project.logs)

        self.node_settings.delete()

        assert_true(self.node_settings.deleted)
        args, kwargs = mock_deauth.call_args
        assert_equal(kwargs, {'add_log': False})

        # Log was not generated
        self.project.reload()
        assert_equal(len(self.project.logs), num_old_logs)

    def test_set_auth(self):
        external_account = create_external_account()
        self.user.external_accounts.append(external_account)
        self.user.save()

        # this should not affect settings implicitly
        original_doi = self.node_settings.dataset_doi

        self.node_settings.set_auth(
            external_account=external_account,
            user=self.user
        )

        # this instance is updated
        assert_equal(
            self.node_settings.external_account,
            external_account
        )
        assert_equal(
            self.node_settings.user_settings,
            self.user_settings
        )
        assert_equal(
            self.node_settings.dataset_doi,
            original_doi
        )

        # user_settings was updated
        assert_true(
            self.user_settings.verify_oauth_access(
                node=self.project,
                external_account=external_account,
            )
        )

    def test_set_auth_wrong_user(self):
        external_account = create_external_account()
        self.user.external_accounts.append(external_account)
        self.user.save()

        with assert_raises(PermissionsError):
            self.node_settings.set_auth(
                external_account=external_account,
                user=UserFactory()
            )

    def test_deauthorize(self):

        self.node_settings.deauthorize(Auth(self.user))

        assert_false(self.node_settings.dataverse_alias)
        assert_false(self.node_settings.dataverse)
        assert_false(self.node_settings.dataset_doi)
        assert_false(self.node_settings.dataset)
        assert_false(self.node_settings.user_settings)


class TestNodeSettingsCallbacks(DataverseAddonTestCase):

    def test_after_fork_by_authorized_dataverse_user(self):
        fork = ProjectFactory()
        clone, message = self.node_settings.after_fork(
            node=self.project, fork=fork, user=self.user_settings.owner
        )
        assert_equal(clone.user_settings, self.user_settings)

    def test_after_fork_by_unauthorized_dataverse_user(self):
        fork = ProjectFactory()
        user = UserFactory()
        clone, message = self.node_settings.after_fork(
            node=self.project, fork=fork, user=user,
            save=True
        )
        assert_is_none(clone.user_settings)

    def test_before_fork(self):
        node = ProjectFactory()
        message = self.node_settings.before_fork(node, self.user)
        assert_true(message)

    def test_before_remove_contributor_message(self):
        message = self.node_settings.before_remove_contributor(
            self.project, self.user)
        assert_true(message)
        assert_in(self.user.fullname, message)
        assert_in(self.project.project_or_component, message)

    def test_after_remove_authorized_dataverse_user_not_self(self):
        message = self.node_settings.after_remove_contributor(
            node=self.project, removed=self.user_settings.owner)
        self.node_settings.save()
        assert_is_none(self.node_settings.user_settings)
        assert_true(message)
        assert_in("You can re-authenticate", message)

    def test_after_remove_authorized_dataverse_user_self(self):
        auth = Auth(user=self.user_settings.owner)
        message = self.node_settings.after_remove_contributor(
            self.project, self.user_settings.owner, auth)
        self.node_settings.save()
        assert_is_none(self.node_settings.user_settings)
        assert_true(message)
        assert_not_in("You can re-authenticate", message)

    def test_after_delete(self):
        self.project.remove_node(Auth(user=self.project.creator))
        # Ensure that changes to node settings have been saved
        self.node_settings.reload()
        assert_true(self.node_settings.user_settings is None)
        assert_true(self.node_settings.dataverse_alias is None)
        assert_true(self.node_settings.dataverse is None)
        assert_true(self.node_settings.dataset_doi is None)
        assert_true(self.node_settings.dataset is None)

    @mock.patch('website.archiver.tasks.archive')
    def test_does_not_get_copied_to_registrations(self, mock_archive):
        registration = self.project.register_node(
            schema=get_default_metaschema(),
            auth=Auth(user=self.project.creator),
            data='hodor',
        )
        assert_false(registration.has_addon('dataverse'))

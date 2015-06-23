import mock
from nose.tools import *

from tests.base import OsfTestCase
from tests.factories import ProjectFactory, AuthUserFactory

from framework.auth import Auth
from website.addons.figshare import model
from website.addons.figshare import exceptions
from website.addons.figshare import settings as figshare_settings


class TestFileGuid(OsfTestCase):

    def setUp(self):
        super(OsfTestCase, self).setUp()
        self.user = AuthUserFactory()
        self.project = ProjectFactory(creator=self.user)
        self.project.add_addon('figshare', auth=Auth(self.user))
        self.node_addon = self.project.get_addon('figshare')
        self.node_addon.figshare_id = 8
        self.node_addon.figshare_type = 'project'
        self.node_addon.save()

    def test_provider(self):
        assert_equal(
            'figshare',
            model.FigShareGuidFile().provider
        )

    def test_path_doesnt_crash_without_addon(self):
        guid = model.FigShareGuidFile(node=self.project, path='/baz/foo/bar')
        self.project.delete_addon('figshare', Auth(self.user))

        assert_is(self.project.get_addon('figshare'), None)

        assert_true(guid.path)
        assert_true(guid.waterbutler_path)

    def test_path_doesnt_crash_nonconfig_addon(self):
        guid = model.FigShareGuidFile(node=self.project, path='/baz/foo/bar')
        self.node_addon.figshare_type = None
        self.node_addon.figshare_id = None
        self.node_addon.save()
        self.node_addon.reload()

        assert_true(guid.path)
        assert_true(guid.waterbutler_path)

    def test_mfr_test_path(self):
        self.node_addon.figshare_type = 'fileset'
        self.node_addon.save()
        self.node_addon.reload()

        guid = model.FigShareGuidFile(file_id=2, article_id=4, node=self.project)
        assert_equal(guid.waterbutler_path, '/2')

    def test_correct_path_project(self):
        guid = model.FigShareGuidFile(file_id=2, article_id=4, node=self.project)
        assert_equal(guid.waterbutler_path, '/4/2')

    def test_unique_identifier(self):
        guid = model.FigShareGuidFile(file_id=2, article_id=4)
        assert_equal(guid.unique_identifier, '42')

    def test_exception_from_response(self):
        mock_response = mock.Mock()
        mock_response.json.return_value = {
            'data': {
                'name': 'Morty',
                'extra': {
                    'status': 'drafts'
                }
            }
        }
        guid = model.FigShareGuidFile(file_id=2, article_id=4)

        with assert_raises(exceptions.FigshareIsDraftError):
            guid._exception_from_response(mock_response)

        assert_equal(guid.name, 'Morty')

    @mock.patch('website.addons.base.requests.get')
    def test_enrich_raises(self, mock_get):
        mock_response = mock.Mock(ok=True, status_code=200)
        mock_get.return_value = mock_response
        mock_response.json.return_value = {
            'data': {
                'name': 'Morty',
                'extra': {
                    'status': 'drafts'
                }
            }
        }

        guid = model.FigShareGuidFile(file_id=2, article_id=4, node=self.project)

        with assert_raises(exceptions.FigshareIsDraftError):
            guid.enrich()

        assert_equal(guid.name, 'Morty')

    @mock.patch('website.addons.base.requests.get')
    def test_enrich_works(self, mock_get):
        mock_response = mock.Mock(ok=True, status_code=200)
        mock_get.return_value = mock_response
        mock_response.json.return_value = {
            'data': {
                'name': 'Morty',
                'extra': {
                    'status': 'Rick'
                }
            }
        }

        guid = model.FigShareGuidFile(file_id=2, article_id=4, node=self.project)

        guid.enrich()

        assert_equal(guid.name, 'Morty')

    def test_node_addon_get_or_create(self):
        guid, _ = self.node_addon.find_or_create_file_guid('/4/2')
        assert_equal(guid.waterbutler_path, '/4/2')
        assert_equal(guid.file_id, '2')
        assert_equal(guid.article_id, '4')

    def test_node_addon_get_or_create_finds(self):
        guid, created = self.node_addon.find_or_create_file_guid('/4/2')
        assert_true(created)

        other, other_created = self.node_addon.find_or_create_file_guid('/4/2')
        assert_false(other_created)
        assert_equal(guid, other)

class TestNodeSettings(OsfTestCase):
    def setUp(self):
        super(TestNodeSettings, self).setUp()
        self.user = AuthUserFactory()
        self.project = ProjectFactory(creator=self.user)

        self.project.add_addon('figshare', auth=Auth(self.user))
        self.project.creator.add_addon('figshare')
        self.node_settings = self.project.get_addon('figshare')
        self.user_settings = self.project.creator.get_addon('figshare')
        self.user_settings.oauth_access_token = 'legittoken'
        self.user_settings.oauth_access_token_secret = 'legittoken'
        self.user_settings.save()
        self.node_settings.user_settings = self.user_settings
        self.node_settings.figshare_id = '123456'
        self.node_settings.figshare_type = 'project'
        self.node_settings.figshare_title = 'singlefile'
        self.node_settings.save()

    def test_complete_true(self):
        assert_true(self.node_settings.has_auth)
        assert_true(self.node_settings.complete)

    def test_complete_false(self):
        self.node_settings.figshare_id = None

        assert_true(self.node_settings.has_auth)
        assert_false(self.node_settings.complete)

    def test_complete_auth_false(self):
        self.node_settings.user_settings = None

        assert_false(self.node_settings.has_auth)
        assert_false(self.node_settings.complete)

class TestCallbacks(OsfTestCase):

    def setUp(self):

        super(TestCallbacks, self).setUp()

        self.user = AuthUserFactory()
        self.consolidated_auth = Auth(user=self.user)
        self.auth = ('test', self.user.api_keys[0]._primary_key)
        self.project = ProjectFactory(creator=self.user)

        self.non_authenticator = AuthUserFactory()
        self.project.add_contributor(
            contributor=self.non_authenticator,
            auth=Auth(self.project.creator),
        )

        self.project.add_addon('figshare', auth=self.consolidated_auth)
        self.project.creator.add_addon('figshare')
        self.node_settings = self.project.get_addon('figshare')
        self.user_settings = self.project.creator.get_addon('figshare')
        self.user_settings.oauth_access_token = 'legittoken'
        self.user_settings.oauth_access_token_secret = 'legittoken'
        self.user_settings.save()
        self.node_settings.user_settings = self.user_settings
        self.node_settings.figshare_id = '123456'
        self.node_settings.figshare_type = 'project'
        self.node_settings.figshare_title = 'singlefile'
        self.node_settings.save()

    def test_update_fields_project(self):
        num_logs = len(self.project.logs)
        # try updating fields
        newfields = {
            'type': 'project',
            'id': '313131',
            'name': 'A PROJECT'
        }
        self.node_settings.update_fields(newfields, self.project, Auth(self.project.creator))
        #check for updated
        assert_equals(self.node_settings.figshare_id, '313131')
        assert_equals(self.node_settings.figshare_type, 'project')
        assert_equals(self.node_settings.figshare_title, 'A PROJECT')
        # check for log added
        assert_equals(len(self.project.logs), num_logs + 1)

    def test_update_fields_fileset(self):
        num_logs = len(self.project.logs)
        # try updating fields
        newfields = {
            'type': 'fileset',
            'id': '313131',
            'name': 'A FILESET'
        }
        self.node_settings.update_fields(newfields, self.project, Auth(self.project.creator))
        #check for updated
        assert_equals(self.node_settings.figshare_id, '313131')
        assert_equals(self.node_settings.figshare_type, 'fileset')
        assert_equals(self.node_settings.figshare_title, 'A FILESET')
        # check for log added
        assert_equals(len(self.project.logs), num_logs + 1)

    def test_update_fields_some_missing(self):
        num_logs = len(self.project.logs)
        # try updating fields
        newfields = {
            'type': 'project',
            'id': '313131',
            'name': 'A PROJECT'
        }
        self.node_settings.update_fields(newfields, self.project, Auth(self.project.creator))
        #check for updated
        assert_equals(self.node_settings.figshare_id, '313131')
        assert_equals(self.node_settings.figshare_title, 'A PROJECT')
        # check for log added
        assert_equals(len(self.project.logs), num_logs + 1)

    def test_update_fields_invalid(self):
        num_logs = len(self.project.logs)
        # try updating fields
        newfields = {
            'adad': 131313,
            'i1513': '313131',
            'titladad': 'A PROJECT'
        }
        self.node_settings.update_fields(newfields, self.project, Auth(self.project.creator))
        #check for updated
        assert_equals(self.node_settings.figshare_id, '123456')
        assert_equals(self.node_settings.figshare_type, 'project')
        assert_equals(self.node_settings.figshare_title, 'singlefile')
        # check for log added
        assert_equals(len(self.project.logs), num_logs)

    def test_api_url_no_user(self):
        self.node_settings.user_settings = None
        self.node_settings.save()
        assert_equal(self.node_settings.api_url, figshare_settings.API_URL)

    def test_api_url(self):
        assert_equal(self.node_settings.api_url, figshare_settings.API_OAUTH_URL)

    def test_before_register_linked_content(self):
        assert_false(
            self.node_settings.before_register(
                self.project,
                self.project.creator
            ) is None
        )

    def test_before_register_no_linked_content(self):
        self.node_settings.figshare_id = None
        assert_true(
            self.node_settings.before_register(
                self.project,
                self.project.creator
            ) is None
        )

    def test_before_remove_contributor_authenticator(self):
        message = self.node_settings.before_remove_contributor(
            self.project, self.project.creator
        )
        assert_true(message)

    def test_before_remove_contributor_not_authenticator(self):
        message = self.node_settings.before_remove_contributor(
            self.project, self.non_authenticator
        )
        assert_false(message)

    def test_after_remove_contributor_authenticator_not_self(self):
        auth = Auth(user=self.non_authenticator)
        msg = self.node_settings.after_remove_contributor(
            self.project, self.project.creator, auth
        )

        assert_in(
            self.project.project_or_component,
            msg
        )
        assert_equal(
            self.node_settings.user_settings,
            None
        )
        assert_in("You can re-authenticate", msg)

    def test_after_remove_contributor_authenticator_self(self):
        msg = self.node_settings.after_remove_contributor(
            self.project, self.project.creator, self.consolidated_auth
        )

        assert_in(
            self.project.title,
            msg
        )
        assert_equal(
            self.node_settings.user_settings,
            None
        )
        assert_not_in("You can re-authenticate", msg)

    def test_after_fork_authenticator(self):
        fork = ProjectFactory()
        clone, message = self.node_settings.after_fork(
            self.project, fork, self.project.creator,
        )
        assert_equal(
            self.node_settings.user_settings,
            clone.user_settings,
        )

    def test_after_fork_not_authenticator(self):
        fork = ProjectFactory()
        clone, message = self.node_settings.after_fork(
            self.project, fork, self.non_authenticator,
        )
        assert_equal(
            clone.user_settings,
            None,
        )

    def test_after_delete(self):
        self.project.remove_node(Auth(user=self.project.creator))
        # Ensure that changes to node settings have been saved
        self.node_settings.reload()
        assert_true(self.node_settings.user_settings is None)
        assert_true(self.node_settings.figshare_id is None)
        assert_true(self.node_settings.figshare_type is None)
        assert_true(self.node_settings.figshare_title is None)

    @mock.patch('website.archiver.tasks.archive.si')
    @mock.patch('website.addons.figshare.model.AddonFigShareNodeSettings.archive_errors')
    def test_does_not_get_copied_to_registrations(self, mock_errors, mock_archive):
        registration = self.project.register_node(
            schema=None,
            auth=Auth(user=self.project.creator),
            template='Template1',
            data='hodor'
        )
        assert_false(registration.has_addon('figshare'))

    #TODO Test figshare options and figshare to_json

from nose.tools import *

from tests.base import OsfTestCase
from tests.factories import ProjectFactory, AuthUserFactory

from framework.auth import Auth
from website.addons.figshare import settings as figshare_settings


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
            'title': 'A PROJECT'
           }
        self.node_settings.update_fields(newfields, self.project, Auth(self.project.creator))
        #check for updated
        assert_equals(self.node_settings.figshare_id, '313131')
        assert_equals(self.node_settings.figshare_type, 'project')
        assert_equals(self.node_settings.figshare_title, 'A PROJECT')
        # check for log added
        assert_equals(len(self.project.logs), num_logs+1)

    def test_update_fields_fileset(self):
        num_logs = len(self.project.logs)
        # try updating fields
        newfields = {
            'type': 'fileset',
            'id': '313131',
            'title': 'A FILESET'
           }
        self.node_settings.update_fields(newfields, self.project, Auth(self.project.creator))
        #check for updated
        assert_equals(self.node_settings.figshare_id, '313131')
        assert_equals(self.node_settings.figshare_type, 'fileset')
        assert_equals(self.node_settings.figshare_title, 'A FILESET')
        # check for log added
        assert_equals(len(self.project.logs), num_logs+1)

    def test_update_fields_some_missing(self):
        num_logs = len(self.project.logs)
        # try updating fields
        newfields = {
            'type': 'project',
            'id': '313131',
            'title': 'A PROJECT'
           }
        self.node_settings.update_fields(newfields, self.project, Auth(self.project.creator))
        #check for updated
        assert_equals(self.node_settings.figshare_id, '313131')
        assert_equals(self.node_settings.figshare_title, 'A PROJECT')
        # check for log added
        assert_equals(len(self.project.logs), num_logs+1)

    def test_update_fields_invalid(self):
        num_logs = len(self.project.logs)
        # try updating fields
        newfields = {
            'adad' : 131313,
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

    def test_after_remove_contributor_authenticator(self):
        msg = self.node_settings.after_remove_contributor(
            self.project, self.project.creator
        )

        assert_in(
                self.project.project_or_component,
                msg
        )
        assert_equal(
            self.node_settings.user_settings,
            None
        )

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

    #TODO Test figshare options and figshare to_json

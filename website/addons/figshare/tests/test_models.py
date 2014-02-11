import mock
import unittest
from nose.tools import *

from tests.base import DbTestCase
from tests.factories import UserFactory, ProjectFactory

from website.addons.base import AddonError
from website.addons.figshare import settings as figshare_settings

class TestCallbacks(DbTestCase):

    def setUp(self):

        super(TestCallbacks, self).setUp()
        
        self.project = ProjectFactory.build()
        self.non_authenticator = UserFactory()
        self.project.add_contributor(
            contributor=self.non_authenticator,
            user=self.project.creator,
        )
        self.project.save()

        self.project.add_addon('figshare')
        self.project.creator.add_addon('figshare')
        self.node_settings = self.project.get_addon('figshare')
        self.user_settings = self.project.creator.get_addon('figshare')
        self.node_settings.user_settings = self.user_settings
        self.node_settings.figshare_id = '123456'
        self.node_settings.save()

    def test_before_page_load_osf_public_fs_public(self):
        self.project.is_public = True
        self.project.save()        
        message = self.node_settings.before_page_load(self.project, self.project.creator)
        
        assert_false(message)
    
    @mock.patch('website.addons.figshare.api.Figshare.article_is_public')
    def test_before_page_load_osf_public_fs_private(self, mock_article_is_public):
        self.project.is_public = True
        self.project.save()        
        mock_article_is_public.return_value = False
        message = self.node_settings.before_page_load(self.project, self.project.creator)
        mock_article_is_public.assert_called_with(
            self.node_settings.figshare_id
        )
        
        assert_true(message)
    
    @mock.patch('website.addons.figshare.api.Figshare.article_is_public')
    def test_before_page_load_osf_private_fs_public(self, mock_article_is_public):
        self.project.is_public = False
        self.project.save()        
        mock_article_is_public.return_value = True
        message = self.node_settings.before_page_load(self.project, self.project.creator)
        mock_article_is_public.assert_called_with(
            self.node_settings.figshare_id
        )
        
        assert_true(message)

    @mock.patch('website.addons.figshare.api.Figshare.article_is_public')    
    def test_before_page_load_osf_private_fs_private(self, mock_article_is_public):
        self.project.is_public = False
        self.project.save()        
        mock_article_is_public.return_value = False
        message = self.node_settings.before_page_load(self.project, self.project.creator)
        mock_article_is_public.assert_called_with(
            self.node_settings.figshare_id
        )
        
        assert_false(message)
        
    def test_before_page_load_not_contributor(self):
        message = self.node_settings.before_page_load(self.project, UserFactory())
        assert_false(message)

    def test_before_page_load_not_logged_in(self):
        message = self.node_settings.before_page_load(self.project, None)
        assert_false(message)

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
        self.node_settings.after_remove_contributor(
            self.project, self.project.creator
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

    @mock.patch('website.addons.github.api.GitHub.branches')
    def test_after_register(self, mock_branches):
        # TODO test registration
        pass

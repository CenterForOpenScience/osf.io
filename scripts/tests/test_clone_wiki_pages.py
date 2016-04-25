from framework.auth.core import Auth

from scripts.clone_wiki_pages import update_wiki_pages

from website.addons.wiki.model import NodeWikiPage

from tests.base import OsfTestCase, get_default_metaschema
from tests.factories import NodeWikiFactory, ProjectFactory, RegistrationFactory, AuthUserFactory
from nose.tools import *


class TestCloneWikiPages(OsfTestCase):

    def setUp(self):
        super(TestCloneWikiPages, self).setUp()
        self.user = AuthUserFactory()
        self.project = ProjectFactory(creator=self.user, is_public=True)

    def set_up_project_with_wiki_page(self):
        self.project_with_wikis = ProjectFactory(creator=self.user, is_public=True)
        self.wiki = NodeWikiFactory(node=self.project_with_wikis)
        self.current_wiki = NodeWikiFactory(node=self.project_with_wikis, version=2, is_current=True)
        return self.project_with_wikis

    def test_project_no_wiki_pages(self):
        update_wiki_pages([self.project])
        assert_equal(self.project.wiki_pages_versions, {})
        assert_equal(self.project.wiki_pages_current, {})

    def test_forked_project_no_wiki_pages(self):
        fork = self.project.fork_node(auth=Auth(self.user))
        update_wiki_pages([fork])
        assert_equal(fork.wiki_pages_versions, {})
        assert_equal(fork.wiki_pages_current, {})

    def test_registration_no_wiki_pages(self):
        registration = RegistrationFactory()
        update_wiki_pages([registration])
        assert_equal(registration.wiki_pages_versions, {})
        assert_equal(registration.wiki_pages_current, {})

    def test_project_wiki_pages_do_not_get_cloned(self):
        project = self.set_up_project_with_wiki_page()
        update_wiki_pages([project])
        assert_equal(project.wiki_pages_versions, {self.wiki.page_name: [self.wiki._id, self.current_wiki._id]})
        assert_equal(project.wiki_pages_current, {self.current_wiki.page_name: self.current_wiki._id})

    def test_forked_project_wiki_pages_created_post_fork_do_not_get_cloned(self):
        fork_creator = AuthUserFactory()
        fork = self.project.fork_node(auth=Auth(fork_creator))
        wiki = NodeWikiFactory(node=fork)
        current_wiki = NodeWikiFactory(node=fork, version=2, is_current=True)
        update_wiki_pages([fork])
        assert_equal(fork.wiki_pages_versions, {wiki.page_name: [wiki._id, current_wiki._id]})
        assert_equal(fork.wiki_pages_current, {wiki.page_name: current_wiki._id})

    def test_forked_project_wiki_pages_created_pre_fork_get_cloned(self):
        project = self.set_up_project_with_wiki_page()
        fork = project.fork_node(auth=Auth(self.user))
        # reset wiki pages for test
        fork.wiki_pages_versions = project.wiki_pages_versions
        fork.wiki_pages_current = project.wiki_pages_current
        fork.save()

        update_wiki_pages([fork])
        wiki_versions = fork.wiki_pages_versions[self.wiki.page_name]

        current_wiki = NodeWikiPage.load(fork.wiki_pages_current[self.current_wiki.page_name])
        assert_equal(current_wiki.node, fork)
        assert_not_equal(current_wiki._id, self.current_wiki._id)

        wiki_version = NodeWikiPage.load(wiki_versions[0])
        assert_equal(wiki_version.node, fork)
        assert_not_equal(wiki_version._id, self.current_wiki._id)

    def test_registration_wiki_pages_created_pre_registration_get_cloned(self):
        project = self.set_up_project_with_wiki_page()
        registration = project.register_node(get_default_metaschema(), Auth(self.user), '', None)
        # reset wiki pages for test
        registration.wiki_pages_versions = project.wiki_pages_versions
        registration.wiki_pages_current = project.wiki_pages_current
        registration.save()

        update_wiki_pages([registration])
        wiki_versions = registration.wiki_pages_versions[self.wiki.page_name]

        current_wiki = NodeWikiPage.load(registration.wiki_pages_current[self.current_wiki.page_name])
        assert_equal(current_wiki.node, registration)
        assert_not_equal(current_wiki._id, self.current_wiki._id)

        wiki_version = NodeWikiPage.load(wiki_versions[0])
        assert_equal(wiki_version.node, registration)
        assert_not_equal(wiki_version._id, self.current_wiki._id)

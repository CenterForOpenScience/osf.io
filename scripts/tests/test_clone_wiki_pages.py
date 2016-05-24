from framework.auth.core import Auth
from framework.mongo import database as db

from scripts.clone_wiki_pages import main

from website.addons.wiki.model import NodeWikiPage
from website.project.model import Node

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
        self.current_wiki = NodeWikiFactory(node=self.project_with_wikis, version=2)
        return self.project_with_wikis

    def tearDown(self):
        super(TestCloneWikiPages, self).tearDown()
        db.node.remove({})

    def test_project_no_wiki_pages(self):
        main()
        assert_equal(self.project.wiki_pages_versions, {})
        assert_equal(self.project.wiki_pages_current, {})

    def test_forked_project_no_wiki_pages(self):
        fork = self.project.fork_node(auth=Auth(self.user))
        main()
        assert_equal(fork.wiki_pages_versions, {})
        assert_equal(fork.wiki_pages_current, {})

    def test_registration_no_wiki_pages(self):
        registration = RegistrationFactory()
        main()
        assert_equal(registration.wiki_pages_versions, {})
        assert_equal(registration.wiki_pages_current, {})

    def test_project_wiki_pages_do_not_get_cloned(self):
        project = self.set_up_project_with_wiki_page()
        main()
        assert_equal(project.wiki_pages_versions, {self.wiki.page_name: [self.wiki._id, self.current_wiki._id]})
        assert_equal(project.wiki_pages_current, {self.current_wiki.page_name: self.current_wiki._id})

    def test_wiki_pages_that_do_not_exist_do_not_get_cloned(self):
        project = ProjectFactory(creator=self.user, is_public=True)
        wiki = NodeWikiFactory(node=project)
        NodeWikiPage.remove_one(wiki._id)
        # deleted wiki record in node.wiki_pages_versions
        assert_in(wiki._id, project.wiki_pages_versions[wiki.page_name])
        main()
        project.reload()
        # wiki_id gets removed from node.wiki_pages_versions
        assert_not_in(wiki._id, project.wiki_pages_versions[wiki.page_name])

    def test_wiki_pages_with_invalid_nodes_are_removed_after_cloning(self):
        project = ProjectFactory(creator=self.user, is_public=True)
        wiki = NodeWikiFactory(node=project)
        fork = project.fork_node(auth=Auth(self.user))
        fork.wiki_pages_versions = project.wiki_pages_versions
        fork.wiki_pages_current = project.wiki_pages_current
        fork.save()

        # Remove original node - wiki.node no longer points to an existing project
        Node.remove_one(project._id)

        # clone wiki page
        main()
        fork.reload()
        cloned_wiki_id = fork.wiki_pages_versions[wiki.page_name][0]
        cloned_wiki = NodeWikiPage.load(cloned_wiki_id)
        assert_equal(cloned_wiki.node._id, fork._id)

        # move original wiki page to unmigratedwikipages collection
        assert_false(db.nodewikipage.find_one({'_id': wiki._id}))
        assert_true(db.unmigratedwikipages.find_one({'_id': wiki._id}))

    def test_forked_project_wiki_pages_created_post_fork_do_not_get_cloned(self):
        fork_creator = AuthUserFactory()
        fork = self.project.fork_node(auth=Auth(fork_creator))
        wiki = NodeWikiFactory(node=fork)
        current_wiki = NodeWikiFactory(node=fork, version=2)
        main()
        assert_equal(fork.wiki_pages_versions, {wiki.page_name: [wiki._id, current_wiki._id]})
        assert_equal(fork.wiki_pages_current, {wiki.page_name: current_wiki._id})

    def test_forked_project_wiki_pages_created_pre_fork_get_cloned(self):
        project = self.set_up_project_with_wiki_page()
        fork = project.fork_node(auth=Auth(self.user))
        # reset wiki pages for test
        fork.wiki_pages_versions = project.wiki_pages_versions
        fork.wiki_pages_current = project.wiki_pages_current
        fork.save()

        main()
        # update_wiki_pages(self.find_node_record(fork._id))
        fork.reload()
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

        main()
        registration.reload()
        wiki_versions = registration.wiki_pages_versions[self.wiki.page_name]

        current_wiki = NodeWikiPage.load(registration.wiki_pages_current[self.current_wiki.page_name])
        assert_equal(current_wiki.node, registration)
        assert_not_equal(current_wiki._id, self.current_wiki._id)

        wiki_version = NodeWikiPage.load(wiki_versions[0])
        assert_equal(wiki_version.node, registration)
        assert_not_equal(wiki_version._id, self.current_wiki._id)

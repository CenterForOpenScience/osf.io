# -*- coding: utf-8 -*-
'''Unit tests for models and their factories.'''
import unittest
from nose.tools import *  # PEP8 asserts

from tests.base import DbTestCase
from framework.auth import User
from framework.bcrypt import check_password_hash
from website.project.model import ApiKey
from tests.factories import (UserFactory, ApiKeyFactory, NodeFactory,
    ProjectFactory, NodeLogFactory, WatchConfigFactory)


class TestUser(DbTestCase):

    def setUp(self):
        self.user = UserFactory()

    def test_factory(self):
        # Clear users
        User.remove()
        user = UserFactory(password="myprecious")
        assert_equal(User.find().count(), 1)
        assert_true(user.username)
        another_user = UserFactory(username="joe@example.com")
        assert_equal(another_user.username, "joe@example.com")
        assert_equal(User.find().count(), 2)
        assert_true(user.check_password("myprecious"))

    def test_is_watching(self):
        # User watches a node
        watched_node = NodeFactory()
        unwatched_node = NodeFactory()
        config = WatchConfigFactory(node=watched_node)
        self.user.watched.append(config)
        self.user.save()
        assert_true(self.user.is_watching(watched_node))
        assert_false(self.user.is_watching(unwatched_node))

    def test_set_password(self):
        user = User(username="nick@cage.com", fullname="Nick Cage", is_registered=True)
        user.set_password("ghostrider")
        user.save()
        assert_true(check_password_hash(user.password, 'ghostrider'))

    def test_check_password(self):
        user = User(username="nick@cage.com", fullname="Nick Cage", is_registered=True)
        user.set_password("ghostrider")
        user.save()
        assert_true(user.check_password("ghostrider"))
        assert_false(user.check_password("ghostride"))


class TestApiKey(DbTestCase):

    def setUp(self):
        pass

    def test_factory(self):
        key = ApiKeyFactory()
        user = UserFactory()
        user.api_keys.append(key)
        user.save()
        assert_equal(len(user.api_keys), 1)
        assert_equal(ApiKey.find().count(), 1)


class TestNode(DbTestCase):

    def setUp(self):
        self.user = UserFactory()
        self.parent = ProjectFactory()
        self.node = NodeFactory.build(creator=self.user)
        self.node.contributors.append(self.user)
        self.node.save()
        self.parent.nodes.append(self.node)
        self.parent.save()

    def test_node_factory(self):
        node = NodeFactory()
        assert_false(node.is_public)

    def test_watching(self):
        # A user watched a node
        user = UserFactory()
        config1 = WatchConfigFactory(node=self.node)
        user.watched.append(config1)
        user.save()
        assert_in(config1._id, self.node.watchconfig__watched)

    def test_url(self):
        url = self.node.url
        assert_equal(url, "/project/{0}/node/{1}/".format(self.parent._primary_key,
                                                        self.node._primary_key))

    def test_watch_url(self):
        url = self.node.watch_url
        assert_equal(url, "/api/v1/project/{0}/node/{1}/watch/"
                                .format(self.parent._primary_key,
                                        self.node._primary_key))

    def test_update_node_wiki(self):
        # user updates the wiki
        self.node.update_node_wiki("home", "Hello world", self.user, api_key=None)
        versions = self.node.wiki_pages_versions
        assert_equal(len(versions['home']), 1)
        # Makes another update
        self.node.update_node_wiki('home', "Hola mundo", self.user, api_key=None)
        # Now there are 2 versions
        assert_equal(len(versions['home']), 2)
        # A log event was saved
        assert_equal(self.node.logs[-1].action, "wiki_updated")


class TestProject(DbTestCase):

    def setUp(self):
        self.user = UserFactory()
        self.project = ProjectFactory(creator=self.user)

    def test_project_factory(self):
        node = ProjectFactory()
        assert_equal(node.category, 'project')

    def test_url(self):
        url = self.project.url
        assert_equal(url, "/project/{0}/".format(self.project._primary_key))

    def test_api_url(self):
        api_url = self.project.api_url
        assert_equal(api_url, "/api/v1/project/{0}/".format(self.project._primary_key))

    def test_watch_url(self):
        watch_url = self.project.watch_url
        assert_equal(watch_url, "/api/v1/project/{0}/watch/".format(self.project._primary_key))

    def test_add_contributor(self):
        # A user is added as a contributor
        user2 = UserFactory()
        self.project.add_contributor(user2)
        self.project.save()
        assert_in(user2, self.project.contributors)
        assert_equal(self.project.logs[-1].action, 'contributor_added')

    def test_remove_contributor(self):
        # A user is added as a contributor
        user2 = UserFactory()
        self.project.add_contributor(user2)
        self.project.save()
        # The user is removed
        self.project.remove_contributor(self.user, contributor=user2, api_key=None)
        assert_not_in(user2, self.project.contributors)

    def test_set_title(self):
        proj = ProjectFactory(title="That Was Then", creator=self.user)
        proj.set_title("This is now", user=self.user)
        proj.save()
        # Title was changed
        assert_equal(proj.title, "This is now")
        # A log event was saved
        latest_log = proj.logs[-1]
        assert_equal(latest_log.action, "edit_title")
        assert_equal(latest_log.params['title_original'], "That Was Then")


class TestNodeLog(DbTestCase):

    def setUp(self):
        pass

    def test_node_log_factory(self):
        log = NodeLogFactory()
        assert_true(log.action)


class TestWatchConfig(DbTestCase):

    def tearDown(self):
        User.remove()

    def test_factory(self):
        config = WatchConfigFactory(digest=True, immediate=False)
        assert_true(config.digest)
        assert_false(config.immediate)
        assert_true(config.node._id)

if __name__ == '__main__':
    unittest.main()

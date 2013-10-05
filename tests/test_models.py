# -*- coding: utf-8 -*-
'''Unit tests for models and their factories.'''
import nose
from nose.tools import *  # PEP8 asserts


from tests.base import OsfTestCase
from framework.auth import User
from framework.bcrypt import check_password_hash
from website.project.model import ApiKey
from tests.factories import (UserFactory, ApiKeyFactory, NodeFactory,
    ProjectFactory, NodeLogFactory, WatchConfigFactory)


class TestUser(OsfTestCase):

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


class TestApiKey(OsfTestCase):

    def setUp(self):
        pass

    def test_factory(self):
        key = ApiKeyFactory()
        user = UserFactory()
        user.api_keys.append(key)
        user.save()
        assert_equal(len(user.api_keys), 1)
        assert_equal(ApiKey.find().count(), 1)


class TestNode(OsfTestCase):

    def setUp(self):
        self.parent = ProjectFactory()
        self.node = NodeFactory()
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


class TestProject(OsfTestCase):

    def setUp(self):
        self.project = ProjectFactory()

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


class TestNodeLog(OsfTestCase):

    def setUp(self):
        pass

    def test_node_log_factory(self):
        log = NodeLogFactory()
        assert_true(log.action)


class TestWatchConfig(OsfTestCase):

    def tearDown(self):
        User.remove()

    def test_factory(self):
        config = WatchConfigFactory(digest=True, immediate=False)
        assert_true(config.digest)
        assert_false(config.immediate)
        assert_true(config.node._id)

if __name__ == '__main__':
    nose.main()

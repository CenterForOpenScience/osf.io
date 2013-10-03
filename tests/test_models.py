# -*- coding: utf-8 -*-
'''Unit tests for models and their factories.'''
import unittest
import nose
from nose.tools import *  # PEP8 asserts

from tests.base import OsfTestCase
from framework.auth import User
from website.project.model import ApiKey
from tests.factories import (UserFactory, ApiKeyFactory, NodeFactory,
    ProjectFactory, NodeLogFactory, WatchConfigFactory)


class TestUser(OsfTestCase):

    def setUp(self):
        pass

    def tearDown(self):
        User.remove()

    def test_factory(self):
        user = UserFactory()
        assert_equal(User.find().count(), 1)
        assert_true(user.username)
        another_user = UserFactory(username="joe@example.com")
        assert_equal(another_user.username, "joe@example.com")
        assert_equal(User.find().count(), 2)


class TestApiKey(OsfTestCase):

    def setUp(self):
        pass

    def tearDown(self):
        User.remove()

    def test_factory(self):
        key = ApiKeyFactory()
        user = UserFactory()
        user.api_keys.append(key)
        user.save()
        assert_equal(len(user.api_keys), 1)
        assert_equal(ApiKey.find().count(), 1)


class TestNode(OsfTestCase):

    def setUp(self):
        pass

    def tearDown(self):
        User.remove()

    def test_node_factory(self):
        node = NodeFactory()
        assert_false(node.is_public)

    def test_project_factory(self):
        node = ProjectFactory()
        assert_equal(node.category, 'project')


class TestNodeLog(OsfTestCase):

    def setUp(self):
        pass

    def tearDown(self):
        User.remove()

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

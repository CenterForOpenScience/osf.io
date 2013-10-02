#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''Unit tests for Node/Project watching.'''
import unittest
from nose.tools import *  # PEP8 asserts
from website.models import User, Node, WatchConfig


class TestWatching(unittest.TestCase):

    def setUp(self):
        # FIXME(sloria): This affects the development database;
        # Assumes a user and Node have been created. Use
        # fixtures/factories later
        self.user = User.find()[0]
        self.node = Node.find()[0]
        # Clear watched list
        self.user.watched = []
        self.user.save()

    def test_watch(self):
        assert_equal(len(self.user.watched), 0)
        # A user watches a WatchConfig
        config = WatchConfig(node=self.node)
        self.user.watch(config)
        assert_equal(len(self.user.watched), 1)

if __name__ == '__main__':
    unittest.main()

# -*- coding: utf-8 -*-
import mock
from urlparse import urlparse
from nose.tools import *  # flake8: noqa
import unittest

from framework.auth import Auth

from website.models import Node, NodeLog

from tests.base import DbIsolationMixin, OsfTestCase
from tests.factories import ProjectFactory
from tests import utils as test_utils

class TestUtilsTests(OsfTestCase):

    def setUp(self):
        super(TestUtilsTests, self).setUp()

        self.node = ProjectFactory()
        self.user = self.node.creator
        self.auth = Auth(self.user)

    def test_assert_logs(self):
        
        def add_log(self):
            self.node.add_log(NodeLog.UPDATED_FIELDS, {}, auth=self.auth)
        wrapped = test_utils.assert_logs(NodeLog.UPDATED_FIELDS, 'node')(add_log)
        wrapped(self)

    def test_assert_logs_fail(self):
        
        def dont_add_log(self):
            pass
        wrapped = test_utils.assert_logs(NodeLog.UPDATED_FIELDS, 'node')(dont_add_log)
        assert_raises(AssertionError, lambda: wrapped(self))

    def test_assert_logs_stacked(self):

        def add_log(self):
            self.node.add_log(NodeLog.UPDATED_FIELDS, {}, auth=self.auth)

        def add_two_logs(self):
            add_log(self)
            self.node.add_log(NodeLog.CONTRIB_ADDED, {}, auth=self.auth)
            
        wrapped = test_utils.assert_logs(NodeLog.UPDATED_FIELDS, 'node', -2)(
            test_utils.assert_logs(NodeLog.CONTRIB_ADDED, 'node')(add_two_logs)
        )
        wrapped(self)

    def test_assert_not_logs_pass(self):

        def dont_add_log(self):
            pass
        wrapped = test_utils.assert_not_logs(NodeLog.UPDATED_FIELDS, 'node')(dont_add_log)
        wrapped(self)

    def test_assert_not_logs_fail(self):

        def add_log(self):
            self.node.add_log(NodeLog.UPDATED_FIELDS, {}, auth=self.auth)
        wrapped = test_utils.assert_not_logs(NodeLog.UPDATED_FIELDS, 'node')(add_log)
        assert_raises(AssertionError, lambda: wrapped(self))



class DbIsolationMixinTests(object):

    @classmethod
    def setUpClass(cls, *a, **kw):
        super(DbIsolationMixinTests, cls).setUpClass(*a, **kw)
        cls.ntest_calls = 0  # If we set this at class scope on DbIsolationMixinTests then it
                             # would be shared across the subclasses. Setting it directly on each
                             # subclass here avoids such bleedthrough.

    def check(self):
        ProjectFactory()
        self.__class__.ntest_calls += 1  # a little goofy, yes; each test gets its own instance
        nexpected = self.__class__.ntest_calls if self.nexpected == 'ntest_calls' else 1
        assert_equal(nexpected, len(Node.find()))

    def test_1(self): self.check()
    def test_2(self): self.check()
    def test_3(self): self.check()


class TestMissingDbIsolationMixin(DbIsolationMixinTests, OsfTestCase):
    nexpected = 'ntest_calls'

class TestOutOfOrderDbIsolationMixin(DbIsolationMixinTests, OsfTestCase, DbIsolationMixin):
    nexpected = 'ntest_calls'

class TestProperlyInstalledDbIsolationMixin(DbIsolationMixinTests, DbIsolationMixin, OsfTestCase):
    nexpected = 'constant'

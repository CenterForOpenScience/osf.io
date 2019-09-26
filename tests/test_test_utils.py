# -*- coding: utf-8 -*-
import mock
from nose.tools import *  # noqa: F403
import unittest

from framework.auth import Auth
from osf.models import AbstractNode, NodeLog

from tests.base import OsfTestCase
from osf_tests.factories import ProjectFactory
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

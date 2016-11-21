# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from nose.tools import assert_equal, assert_in, assert_not_in

from modularodm import Q

from framework.auth.core import User
from tests import factories
from tests.base import DbIsolationMixin
from tests.test_search import OsfTestCase
from tests.test_search.test_permissions.test_nodefuncs import proj, PUBLIC
from website.util import permissions
from website.project.model import Node


def anon(node):
    return None


def auth(node):
    return factories.AuthUserFactory().auth


def read(node):
    user = factories.AuthUserFactory()
    node.add_contributor(user, permissions.READ)
    return user.auth


class TestPermFuncs(DbIsolationMixin, OsfTestCase):

    @staticmethod
    def get_user_id_from_authtuple(authtuple):
        return User.find_one(Q('emails', 'eq', authtuple[0]))._id


    # anon

    def test_anon_returns_none(self):
        assert_equal(anon(proj(PUBLIC)), None)

    def test_anon_makes_no_user(self):
        anon(proj(PUBLIC))
        assert_equal(len(User.find()), 1)  # only the project creator


    # auth

    def test_auth_returns_authtuple(self):
        assert_equal(auth(proj(PUBLIC))[1], 'password')

    def test_auth_creates_a_user(self):
        auth(proj(PUBLIC))
        assert_equal(len(User.find()), 2)  # project creator + 1

    def test_auth_user_is_not_a_contributor_on_the_node(self):
        user_id = self.get_user_id_from_authtuple(auth(proj(PUBLIC)))
        assert_not_in(user_id, Node.find_one().permissions.keys())


    # read

    def test_read_returns_authtuple(self):
        assert_equal(read(proj(PUBLIC))[1], 'password')

    def test_read_creates_a_user(self):
        read(proj(PUBLIC))
        assert_equal(len(User.find()), 2)  # project creator + 1

    def test_read_user_is_a_contributor_on_the_node(self):
        user_id = self.get_user_id_from_authtuple(read(proj(PUBLIC)))
        assert_in(user_id, Node.find_one().permissions.keys())

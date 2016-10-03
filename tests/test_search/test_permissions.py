# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import sys
import unittest
import unittest.case

from nose.tools import *  # noqa PEP8 asserts

from framework.auth.core import User
from modularodm import Q
from nose_parameterized import parameterized
from tests import factories
from tests.base import DbIsolationMixin
from tests.test_search import OsfTestCase, SearchTestCase
from tests.utils import mock_archive
from website.files.models.base import File
from website.project.model import Node
from website.util import api_url_for, permissions


PRIVATE, PUBLIC = range(2)
PROJECT, COMPONENT = 'project component'.split()


# nodefuncs

def proj(status=PUBLIC):
    project = factories.ProjectFactory(title='Flim Flammity', is_public=status is PUBLIC)
    project.update_search()
    return project

def comp(status=PUBLIC):
    project = factories.ProjectFactory(title='Slim Slammity', is_public=status is PUBLIC)
    project.update_search()
    component = factories.NodeFactory(
        title='Flim Flammity',
        parent=project,
        is_public=status is PUBLIC,
    )
    component.update_search()
    return component


class TestNodeFuncs(DbIsolationMixin, OsfTestCase):

    def test_there_are_no_nodes_to_start_with(self):
        assert Node.find().count() == 0


    # proj

    def test_proj_makes_private_project_private(self):
        proj(PRIVATE)
        assert not Node.find_one().is_public

    def test_proj_makes_public_project_public(self):
        proj(PUBLIC)
        assert Node.find_one().is_public


    # comp

    def test_comp_makes_private_component_private(self):
        comp(PRIVATE)
        assert not Node.find_one(Q('parent_node', 'ne', None)).is_public

    def test_comp_makes_public_component_public(self):
        comp(PUBLIC)
        assert Node.find_one(Q('parent_node', 'ne', None)).is_public


# permfuncs

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


# varyfuncs

def base(node):
    type_ = 'project' if node.parent_node is None else 'component'
    return 'flim', type_, 'title', 'Flim Flammity'

def file_on(node):
    node.get_addon('osfstorage').get_root().append_file('Blim Blammity')
    return 'blim', 'file', 'name', 'Blim Blammity'

def registration_of(node):
    mock_archive(node, autocomplete=True, autoapprove=True).__enter__()  # ?!
    return 'flim', 'registration', 'title', 'Flim Flammity'


class TestVaryFuncs(DbIsolationMixin, OsfTestCase):

    # base

    def test_base_specifies_project_for_project(self):
        assert_equal(base(proj())[1], 'project')

    def test_base_specifies_component_for_component(self):
        assert_equal(base(comp())[1], 'component')


    # fo - file_on

    def test_fo_makes_a_file_on_a_node(self):
        file_on(factories.ProjectFactory())
        assert_equal(File.find_one(Q('is_file', 'eq', True)).name, 'Blim Blammity')


    # ro - registration_of

    def test_ro_makes_a_registration_of_a_node(self):
        registration_of(factories.ProjectFactory(title='Flim Flammity'))
        assert_equal(Node.find_one(Q('is_registration', 'eq', True)).title, 'Flim Flammity')


# gettin' it together

def namefunc(varyfunc, status, nodefunc, included, permfunc, **_):
    return "{}{} {} {} {}".format(
        '' if varyfunc is base else varyfunc.__name__.replace('_', ' ') + ' ',
        'private' if status is PRIVATE else 'public',
        'project' if nodefunc is proj else 'component',
        'shown to' if included else 'hidden from',
        permfunc.__name__
    )

def generate_cases():
    for status in (PRIVATE, PUBLIC):
        for nodefunc in (proj, comp):
            for permfunc in (anon, auth, read):
                included = permfunc is read if status is PRIVATE else True
                for varyfunc in (base, file_on, registration_of):
                    if status is PRIVATE and varyfunc is registration_of: continue
                    yield namefunc(**locals()), varyfunc, nodefunc, status, permfunc, included


class TestGenerateCases(unittest.TestCase):

    # gc - generate_cases

    def test_gc_generates_cases(self):
        assert_equal(len(list(generate_cases())), 30)

    def test_gc_doesnt_create_any_nodes(self):
        list(generate_cases())
        assert_equal(len(Node.find()), 0)


def possiblyExpectFailure(case):

    # This is a hack to conditionally wrap a failure expectation around *some*
    # of the cases we're feeding to node-parameterized. TODO It can be removed
    # when we write the code to unfail the tests.

    def test(*a, **kw):  # name must start with test or it's ignored
        _, _, _, _, status, permfunc, _ = a
        if status is PRIVATE and permfunc is read:

            # This bit is copied from the unittest/case.py:expectedFailure
            # decorator.

            try:
                return case(*a, **kw)
            except Exception:
                raise unittest.case._ExpectedFailure(sys.exc_info())
            raise unittest.case._UnexpectedSuccess
        else:
            return case(*a, **kw)
    return test


class TestSearchSearchAPI(SearchTestCase):
    """Exercises the website.search.views.search_search view.
    """

    def results(self, query, category, auth):
        url = api_url_for('search_search')
        data = {'q': 'category:{} AND {}'.format(category, query)}
        return self.app.get(url, data, auth=auth).json['results']

    @parameterized.expand(generate_cases)
    @possiblyExpectFailure
    def test(self, ignored, varyfunc, nodefunc, status, permfunc, included):
        node = nodefunc(status)
        auth = permfunc(node)
        query, type_, key, expected_name = varyfunc(node)
        expected = [(expected_name, type_)] if included else []
        results = self.results(query, type_, auth)
        assert_equal([(x[key], x['category']) for x in results], expected)

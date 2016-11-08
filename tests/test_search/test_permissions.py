# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import re
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

def _register(*a, **kw):
    mock_archive(*a, **kw).__enter__()  # gooooooofffyyyyyy
    return 'flim', 'registration', 'title', 'Flim Flammity'

def name_regfunc(embargo, autoapprove, autocomplete, retraction, autoapprove_retraction, **_):
    retraction_part = '' if not retraction else \
                      '{}_retraction_of_an_'.format('approved' if autoapprove_retraction else
                                                    'unapproved')
    return '{}{}_{}_{}_registration_of'.format(
        retraction_part,
        'embargoed' if embargo else 'unembargoed',
        'approved' if autoapprove else 'unapproved',
        'complete' if autocomplete else 'incomplete',
    ).encode('ascii')

def create_regfunc(**kw):
    def regfunc(node):
        return _register(node, **kw)
    regfunc.__name__ = name_regfunc(**kw)
    return regfunc

def create_regfuncs():
    public = set()
    private = set()
    # Default values are listed first for all of these ...
    for embargo in (False, True):
        for autoapprove in (False, True):
            for autocomplete in (True, False):
                for autoapprove_retraction in (None, False):  # TODO
                    retraction = autoapprove_retraction is not None

                    if retraction and not (autoapprove or embargo):
                        continue  # 'Only public or embargoed registrations may be withdrawn.'

                    regfunc = create_regfunc(
                        embargo=embargo,
                        retraction=retraction,
                        autoapprove_retraction=autoapprove_retraction,
                        autocomplete=autocomplete,
                        autoapprove=autoapprove,
                    )
                    should_be_public = (not embargo) and autoapprove and autocomplete
                    (public if should_be_public else private).add(regfunc)
    return public, private

REGFUNCS_PUBLIC, REGFUNCS_PRIVATE = create_regfuncs()
REGFUNCS = REGFUNCS_PUBLIC | REGFUNCS_PRIVATE

locals_dict = locals()
for regfunc in REGFUNCS:
    locals_dict[regfunc.__name__] = regfunc

VARYFUNCS = (
    base,
    file_on,
) + tuple(REGFUNCS)

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


    # regfuncs

    def Reg(self, func):
        func(factories.ProjectFactory(title='Flim Flammity'))
        return Node.find_one(Q('is_registration', 'eq', True))

    def test_number_of_regfuncs(self):
        assert_equal(len(REGFUNCS), 14)

    def test_number_of_regfunc_tests(self):
        is_regfunc_test = lambda n: re.match('test_.*makes_an_.*_registration_of_a_node', n)
        regfunc_tests = filter(is_regfunc_test, self.__class__.__dict__.keys())
        assert_equal(len(regfunc_tests), len(REGFUNCS))

    # no retraction
    def test_uacro_makes_an_unembargoed_approved_complete_registration_of_a_node(self):
        reg = self.Reg(unembargoed_approved_complete_registration_of)
        ok_(reg.retraction is None)
        ok_(not reg.embargo)
        assert_equal(reg.registration_approval.state, 'approved')
        ok_(reg.archive_job.done)

    def test_uairo_makes_an_unembargoed_approved_incomplete_registration_of_a_node(self):
        reg = self.Reg(unembargoed_approved_incomplete_registration_of)
        ok_(reg.retraction is None)
        ok_(not reg.embargo)
        assert_equal(reg.registration_approval.state, 'approved')
        ok_(not reg.archive_job.done)

    def test_uucro_makes_an_unembargoed_unapproved_complete_registration_of_a_node(self):
        reg = self.Reg(unembargoed_unapproved_complete_registration_of)
        ok_(reg.retraction is None)
        ok_(not reg.embargo)
        assert_equal(reg.registration_approval.state, 'unapproved')
        ok_(reg.archive_job.done)

    def test_uuiro_makes_an_unembargoed_unapproved_incomplete_registration_of_a_node(self):
        reg = self.Reg(unembargoed_unapproved_incomplete_registration_of)
        ok_(reg.retraction is None)
        ok_(not reg.embargo)
        assert_equal(reg.registration_approval.state, 'unapproved')
        ok_(not reg.archive_job.done)

    def test_eacro_makes_an_embargoed_approved_complete_registration_of_a_node(self):
        reg = self.Reg(embargoed_approved_complete_registration_of)
        ok_(reg.retraction is None)
        assert_equal(reg.embargo.state, 'approved')
        ok_(reg.archive_job.done)

    def test_eairo_makes_an_embargoed_approved_incomplete_registration_of_a_node(self):
        reg = self.Reg(embargoed_approved_incomplete_registration_of)
        ok_(reg.retraction is None)
        assert_equal(reg.embargo.state, 'approved')
        ok_(not reg.archive_job.done)

    def test_eucro_makes_an_embargoed_unapproved_complete_registration_of_a_node(self):
        reg = self.Reg(embargoed_unapproved_complete_registration_of)
        ok_(reg.retraction is None)
        assert_equal(reg.embargo.state, 'unapproved')
        ok_(reg.archive_job.done)

    def test_euiro_makes_an_embargoed_unapproved_incomplete_registration_of_a_node(self):
        reg = self.Reg(embargoed_unapproved_incomplete_registration_of)
        ok_(reg.retraction is None)
        assert_equal(reg.embargo.state, 'unapproved')
        ok_(not reg.archive_job.done)

    # unapproved retraction
    def test_urouacro_makes_an_unapproved_retraction_of_an_unembargoed_approved_complete_registration_of_a_node(self):
        reg = self.Reg(unapproved_retraction_of_an_unembargoed_approved_complete_registration_of)
        assert_equal(reg.retraction.state, 'unapproved')
        ok_(not reg.embargo)
        assert_equal(reg.registration_approval.state, 'approved')
        ok_(reg.archive_job.done)

    def test_urouairo_makes_an_unapproved_retraction_of_an_unembargoed_approved_incomplete_registration_of_a_node(self):
        reg = self.Reg(unapproved_retraction_of_an_unembargoed_approved_incomplete_registration_of)
        assert_equal(reg.retraction.state, 'unapproved')
        ok_(not reg.embargo)
        assert_equal(reg.registration_approval.state, 'approved')
        ok_(not reg.archive_job.done)

    def test_uroeacro_makes_an_unapproved_retraction_of_an_embargoed_approved_complete_registration_of_a_node(self):
        reg = self.Reg(unapproved_retraction_of_an_embargoed_approved_complete_registration_of)
        assert_equal(reg.retraction.state, 'unapproved')
        assert_equal(reg.embargo.state, 'approved')
        ok_(reg.archive_job.done)

    def test_uroeairo_makes_an_unapproved_retraction_of_an_embargoed_approved_incomplete_registration_of_a_node(self):
        reg = self.Reg(unapproved_retraction_of_an_embargoed_approved_incomplete_registration_of)
        assert_equal(reg.retraction.state, 'unapproved')
        assert_equal(reg.embargo.state, 'approved')
        ok_(not reg.archive_job.done)

    def test_uroeucro_makes_an_unapproved_retraction_of_an_embargoed_unapproved_complete_registration_of_a_node(self):
        reg = self.Reg(unapproved_retraction_of_an_embargoed_unapproved_complete_registration_of)
        assert_equal(reg.retraction.state, 'unapproved')
        assert_equal(reg.embargo.state, 'unapproved')
        ok_(reg.archive_job.done)

    def test_uroeuiro_makes_an_unapproved_retraction_of_an_embargoed_unapproved_incomplete_registration_of_a_node(self):
        reg = self.Reg(unapproved_retraction_of_an_embargoed_unapproved_incomplete_registration_of)
        assert_equal(reg.retraction.state, 'unapproved')
        assert_equal(reg.embargo.state, 'unapproved')
        ok_(not reg.archive_job.done)


# gettin' it together

def namefunc(varyfunc, status, nodefunc, should_see, permfunc, **_):
    return "{}{} {} {} {}".format(
        '' if varyfunc is base else varyfunc.__name__.replace('_', ' ') + ' ',
        'private' if status is PRIVATE else 'public',
        'project' if nodefunc is proj else 'component',
        'shown to' if should_see else 'hidden from',
        permfunc.__name__
    )

def seefunc(status, varyfunc, permfunc, default__TODO_remove_this_argument=True):
    if status is PRIVATE or varyfunc in REGFUNCS_PRIVATE:
        return permfunc is read
    return default__TODO_remove_this_argument

def generate_cases():
    for status in (PRIVATE, PUBLIC):
        for nodefunc in (proj, comp):
            for permfunc in (anon, auth, read):
                for varyfunc in VARYFUNCS:
                    if status is PRIVATE and varyfunc in REGFUNCS: continue
                    should_see = seefunc(status, varyfunc, permfunc)  # namefunc wants this
                    yield namefunc(**locals()), varyfunc, nodefunc, status, permfunc, should_see


class TestGenerateCases(unittest.TestCase):

    # gc - generate_cases

    def test_gc_generates_cases(self):
        assert_equal(len(list(generate_cases())), 108)

    def test_gc_doesnt_create_any_nodes(self):
        list(generate_cases())
        assert_equal(len(Node.find()), 0)


def possiblyExpectFailure(case):

    # This is a hack to conditionally wrap a failure expectation around *some*
    # of the cases we're feeding to node-parameterized. TODO It can be removed
    # when we write the code to unfail the tests.

    def test(*a, **kw):  # name must start with test or it's ignored
        _, _, varyfunc, _, status, permfunc, _ = a
        if seefunc(status, varyfunc, permfunc, False):

            # This bit is copied from the unittest/case.py:expectedFailure
            # decorator.

            try:
                case(*a, **kw)
            except Exception:
                raise unittest.case._ExpectedFailure(sys.exc_info())
            raise unittest.case._UnexpectedSuccess
        else:
            case(*a, **kw)
    return test


class TestSearchSearchAPI(SearchTestCase):
    """Exercises the website.search.views.search_search view.
    """

    def search(self, query, category, auth):
        url = api_url_for('search_search')
        data = {'q': 'category:{} AND {}'.format(category, query)}
        return self.app.get(url, data, auth=auth).json['results']

    @parameterized.expand(generate_cases)
    @possiblyExpectFailure
    def test(self, ignored, varyfunc, nodefunc, status, permfunc, should_see):
        node = nodefunc(status)
        auth = permfunc(node)
        query, type_, key, expected_name = varyfunc(node)
        expected = [(expected_name, type_)] if should_see else []
        results = self.search(query, type_, auth)
        assert_equal([(x[key], x['category']) for x in results], expected)

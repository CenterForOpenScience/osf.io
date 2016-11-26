# -*- coding: utf-8 -*-
"""This is a test suite for permissions on the search_search endpoint. It has four parts:

    - nodefuncs - functions that return Nodes
    - permfuncs - functions that set permissions on a Node
    - varyfuncs - functions that vary the (non-permission) state of a Node
    - TestSearchSearchAPI - the actual tests against the search_search API,
      which are generated from the combinations of the above three function types

"""
from __future__ import absolute_import, division, print_function, unicode_literals

import sys
import unittest
import unittest.case

from nose.tools import assert_equal

from nose_parameterized import parameterized
from tests.test_search import SearchTestCase
from tests.test_search.test_permissions.test_varyfuncs import VARYFUNCS, REGFUNCS, REGFUNCS_PRIVATE
from tests.test_search.test_permissions.test_varyfuncs import base
from tests.test_search.test_permissions.test_permfuncs import anon, auth, read
from tests.test_search.test_permissions.test_nodefuncs import NODEFUNCS, NODEFUNCS_PRIVATE
from website.project.model import Node
from website.util import api_url_for


def determine_case_name(nodefunc, permfunc, varyfunc, should_see, **_):
    return "{}{} {} {}".format(
        '' if varyfunc is base else varyfunc.__name__.replace('_', ' ') + ' ',
        ' '.join(nodefunc.__name__.split('_')),
        'shown to' if should_see else 'hidden from',
        permfunc.__name__
    )


def determine_should_see(nodefunc, permfunc, varyfunc, default__TODO_remove_this_argument=True):
    if nodefunc in NODEFUNCS_PRIVATE or varyfunc in REGFUNCS_PRIVATE:
        return permfunc is read
    return default__TODO_remove_this_argument


def want(name):
    # filter cases since we can't use nose's usual mechanisms with parameterization
    return True


def generate_cases():
    for nodefunc in NODEFUNCS:
        for permfunc in (anon, auth, read):
            for varyfunc in VARYFUNCS:
                if nodefunc in NODEFUNCS_PRIVATE and varyfunc in REGFUNCS:
                    # Registration makes a node public, so skip it.
                    continue
                should_see = determine_should_see(nodefunc, permfunc, varyfunc)
                name = determine_case_name(**locals())
                if want(name):
                    yield name, nodefunc, permfunc, varyfunc, should_see


class TestGenerateCases(unittest.TestCase):

    # gc - generate_cases

    def test_gc_generates_cases(self):
        assert_equal(len(list(generate_cases())), 156)

    def test_gc_doesnt_create_any_nodes(self):
        list(generate_cases())
        assert_equal(len(Node.find()), 0)


def possiblyExpectFailure(case):

    # This is a hack to conditionally wrap a failure expectation around *some*
    # of the cases we're feeding to node-parameterized. TODO It can be removed
    # when we write the code to unfail the tests.

    def test(*a, **kw):  # name must start with test or it's ignored
        _, _, nodefunc, permfunc, varyfunc, _ = a
        if determine_should_see(nodefunc, permfunc, varyfunc, False):

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
    def test(self, ignored, nodefunc, permfunc, varyfunc, should_see):
        node = nodefunc()
        auth = permfunc(node)
        query, type_, key, expected_name = varyfunc(node)
        expected = [(expected_name, type_)] if should_see else []
        results = self.search(query, type_, auth)
        assert_equal([(x[key], x['category']) for x in results], expected)

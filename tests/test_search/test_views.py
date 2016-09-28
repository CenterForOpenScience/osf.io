# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import unittest

from nose.tools import *  # noqa PEP8 asserts
from nose_parameterized import parameterized

from modularodm import Q

from framework.auth.core import User
from tests import factories
from tests.base import DbIsolationMixin
from tests.test_search import OsfTestCase, SearchTestCase
from tests.utils import mock_archive
from website.files.models.base import File
from website.project.model import Node
from website.util import api_url_for, permissions


class TestSearchPage(SearchTestCase):

    def test_search_projects(self):
        factories.ProjectFactory(title='Foo Bar')
        res = self.app.get('/search/', {'q': 'foo'})
        assert_equal(res.status_code, 200)


###################################################################################################
# Search Permissions Tests

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


class TestSearchSearchAPI(SearchTestCase):
    """Exercises the website.search.views.search_search view.
    """

    def results(self, query, category, auth):
        url = api_url_for('search_search')
        data = {'q': 'category:{} AND {}'.format(category, query)}
        return self.app.get(url, data, auth=auth).json['results']

    @parameterized.expand(generate_cases)
    def test(self, ignored, varyfunc, nodefunc, status, permfunc, included):
        node = nodefunc(status)
        auth = permfunc(node)
        query, type_, key, expected_name = varyfunc(node)
        expected = [(expected_name, type_)] if included else []
        results = self.results(query, type_, auth)
        assert_equal([(x[key], x['category']) for x in results], expected)

#
###################################################################################################


class TestUserSearchAPI(SearchTestCase):

    def setUp(self):
        super(TestUserSearchAPI, self).setUp()
        import website.search.search as search
        search.delete_all()

        robbie = factories.UserFactory(fullname='Robbie Williams')
        self.project = factories.ProjectFactory(creator=robbie)
        self.contrib = factories.UserFactory(fullname='Brian May')
        for i in range(0, 12):
            factories.UserFactory(fullname='Freddie Mercury{}'.format(i))

    def tearDown(self):
        super(TestUserSearchAPI, self).tearDown()
        import website.search.search as search
        search.delete_all()

    def test_search_contributor(self):
        url = api_url_for('search_contributor')
        res = self.app.get(url, {'query': self.contrib.fullname})
        assert_equal(res.status_code, 200)
        result = res.json['users']
        assert_equal(len(result), 1)
        brian = result[0]
        assert_equal(brian['fullname'], self.contrib.fullname)
        assert_in('gravatar_url', brian)
        assert_equal(brian['registered'], self.contrib.is_registered)
        assert_equal(brian['active'], self.contrib.is_active)

    def test_search_pagination_default(self):
        url = api_url_for('search_contributor')
        res = self.app.get(url, {'query': 'fr'})
        assert_equal(res.status_code, 200)
        result = res.json['users']
        pages = res.json['pages']
        page = res.json['page']
        assert_equal(len(result), 5)
        assert_equal(pages, 3)
        assert_equal(page, 0)

    def test_search_pagination_default_page_1(self):
        url = api_url_for('search_contributor')
        res = self.app.get(url, {'query': 'fr', 'page': 1})
        assert_equal(res.status_code, 200)
        result = res.json['users']
        page = res.json['page']
        assert_equal(len(result), 5)
        assert_equal(page, 1)

    def test_search_pagination_default_page_2(self):
        url = api_url_for('search_contributor')
        res = self.app.get(url, {'query': 'fr', 'page': 2})
        assert_equal(res.status_code, 200)
        result = res.json['users']
        page = res.json['page']
        assert_equal(len(result), 2)
        assert_equal(page, 2)

    def test_search_pagination_smaller_pages(self):
        url = api_url_for('search_contributor')
        res = self.app.get(url, {'query': 'fr', 'size': 5})
        assert_equal(res.status_code, 200)
        result = res.json['users']
        pages = res.json['pages']
        page = res.json['page']
        assert_equal(len(result), 5)
        assert_equal(page, 0)
        assert_equal(pages, 3)

    def test_search_pagination_smaller_pages_page_2(self):
        url = api_url_for('search_contributor')
        res = self.app.get(url, {'query': 'fr', 'page': 2, 'size': 5, })
        assert_equal(res.status_code, 200)
        result = res.json['users']
        pages = res.json['pages']
        page = res.json['page']
        assert_equal(len(result), 2)
        assert_equal(page, 2)
        assert_equal(pages, 3)


class TestODMTitleSearchAPI(SearchTestCase):
    """ Docs from original method:
    :arg term: The substring of the title.
    :arg category: Category of the node.
    :arg isDeleted: yes, no, or either. Either will not add a qualifier for that argument in the search.
    :arg isFolder: yes, no, or either. Either will not add a qualifier for that argument in the search.
    :arg isRegistration: yes, no, or either. Either will not add a qualifier for that argument in the search.
    :arg includePublic: yes or no. Whether the projects listed should include public projects.
    :arg includeContributed: yes or no. Whether the search should include projects the current user has
        contributed to.
    :arg ignoreNode: a list of nodes that should not be included in the search.
    :return: a list of dictionaries of projects
    """
    def setUp(self):
        super(TestODMTitleSearchAPI, self).setUp()

        self.user = factories.AuthUserFactory()
        self.user_two = factories.AuthUserFactory()
        self.project = factories.ProjectFactory(creator=self.user, title="foo")
        self.project_two = factories.ProjectFactory(creator=self.user_two, title="bar")
        self.public_project = factories.ProjectFactory(creator=self.user_two, is_public=True, title="baz")
        self.registration_project = factories.RegistrationFactory(creator=self.user, title="qux")
        self.folder = factories.CollectionFactory(creator=self.user, title="quux")
        self.dashboard = factories.BookmarkCollectionFactory(creator=self.user, title="Dashboard")
        self.url = api_url_for('search_projects_by_title')

    def test_search_projects_by_title(self):
        res = self.app.get(self.url, {'term': self.project.title}, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(len(res.json), 1)
        res = self.app.get(self.url,
                           {
                               'term': self.public_project.title,
                               'includePublic': 'yes',
                               'includeContributed': 'no'
                           }, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(len(res.json), 1)
        res = self.app.get(self.url,
                           {
                               'term': self.project.title,
                               'includePublic': 'no',
                               'includeContributed': 'yes'
                           }, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(len(res.json), 1)
        res = self.app.get(self.url,
                           {
                               'term': self.project.title,
                               'includePublic': 'no',
                               'includeContributed': 'yes',
                               'isRegistration': 'no'
                           }, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(len(res.json), 1)
        res = self.app.get(self.url,
                           {
                               'term': self.project.title,
                               'includePublic': 'yes',
                               'includeContributed': 'yes',
                               'isRegistration': 'either'
                           }, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(len(res.json), 1)
        res = self.app.get(self.url,
                           {
                               'term': self.public_project.title,
                               'includePublic': 'yes',
                               'includeContributed': 'yes',
                               'isRegistration': 'either'
                           }, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(len(res.json), 1)
        res = self.app.get(self.url,
                           {
                               'term': self.registration_project.title,
                               'includePublic': 'yes',
                               'includeContributed': 'yes',
                               'isRegistration': 'either'
                           }, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(len(res.json), 2)
        res = self.app.get(self.url,
                           {
                               'term': self.registration_project.title,
                               'includePublic': 'yes',
                               'includeContributed': 'yes',
                               'isRegistration': 'no'
                           }, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(len(res.json), 1)
        res = self.app.get(self.url,
                           {
                               'term': self.folder.title,
                               'includePublic': 'yes',
                               'includeContributed': 'yes',
                               'isFolder': 'yes'
                           }, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 404)
        res = self.app.get(self.url,
                           {
                               'term': self.folder.title,
                               'includePublic': 'yes',
                               'includeContributed': 'yes',
                               'isFolder': 'no'
                           }, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(len(res.json), 0)
        res = self.app.get(self.url,
                           {
                               'term': self.dashboard.title,
                               'includePublic': 'yes',
                               'includeContributed': 'yes',
                               'isFolder': 'no'
                           }, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(len(res.json), 0)
        res = self.app.get(self.url,
                           {
                               'term': self.dashboard.title,
                               'includePublic': 'yes',
                               'includeContributed': 'yes',
                               'isFolder': 'yes'
                           }, auth=self.user.auth, expect_errors=True)
        assert_equal(res.status_code, 404)

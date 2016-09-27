# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import unittest

from nose.tools import *  # noqa PEP8 asserts
from nose_parameterized import parameterized

from modularodm import Q

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

def make_project(status):
    project = factories.ProjectFactory(title='Flim Flammity', is_public=status is PUBLIC)
    project.update_search()
    return project

def make_registration(status):
    project = factories.ProjectFactory(title='Flim Flammity', is_public=status is PUBLIC)
    mock_archive(project, autocomplete=True, autoapprove=True).__enter__()  # ?!
    return project

def make_component(status):
    project = factories.ProjectFactory(title='Blim Blammity', is_public=status is PUBLIC)
    project.update_search()
    component = factories.NodeFactory(
        title='Flim Flammity',
        parent=project,
        is_public=status is PUBLIC,
    )
    component.update_search()
    return component

def make_file(status):
    project = factories.ProjectFactory(title='Blim Blammity', is_public=status is PUBLIC)
    project.get_addon('osfstorage').get_root().append_file('Flim Flammity')
    return project


class TestMakers(DbIsolationMixin, OsfTestCase):

    def test_there_are_no_nodes_to_start_with(self):
        assert Node.find().count() == 0


    # mp - make_project

    def test_mp_makes_private_project_private(self):
        make_project(PRIVATE)
        assert not Node.find_one().is_public

    def test_mp_makes_public_project_public(self):
        make_project(PUBLIC)
        assert Node.find_one().is_public


    # mr - make_registration

    def test_mr_makes_private_registration_public_there_are_no_private_registrations(self):
        # TODO Instead we need to test the different approval/embargo workflow states
        make_registration(PRIVATE)
        assert Node.find_one(Q('is_registration', 'eq', True)).is_public

    def test_mr_makes_public_registration_public(self):
        make_registration(PUBLIC)
        assert Node.find_one(Q('is_registration', 'eq', True)).is_public


    # mc - make_component

    def test_mc_makes_private_component_private(self):
        make_component(PRIVATE)
        assert not Node.find_one(Q('parent_node', 'ne', None)).is_public

    def test_mc_makes_public_component_public(self):
        make_component(PUBLIC)
        assert Node.find_one(Q('parent_node', 'ne', None)).is_public


    # mf - make_file

    def test_mf_makes_private_file_private(self):
        make_file(PRIVATE)
        # Looks like privacy attaches to the node, not the file
        assert not File.find_one(Q('is_file', 'eq', True)).node.is_public

    def test_mf_makes_public_file_public(self):
        make_file(PUBLIC)
        assert File.find_one(Q('is_file', 'eq', True)).node.is_public


PRIVATE, PUBLIC = range(2)
PROJECT, REGISTRATION, COMPONENT, FILE = 'project registration component file'.split()
ANON, AUTH, READ = (None, [], [permissions.READ])

def get_test_name(status, type_, included, perms, **_):
    return "{} {} {} {}".format(
        'private' if status is PRIVATE else 'public',
        type_,
        'shown to' if included else 'hidden from',
        'anon' if perms is ANON else 'auth' if perms is AUTH else 'read'
    )

MAKERS = {
    PROJECT: make_project,
    REGISTRATION: make_registration,
    COMPONENT: make_component,
    FILE: make_file,
}

def generate_cases():
    for status in (PRIVATE, PUBLIC):
        for type_ in (PROJECT, REGISTRATION, COMPONENT, FILE):
            make = MAKERS[type_]
            if status is PRIVATE and type_ is REGISTRATION: continue
            for perms in (ANON, AUTH, READ):
                included = perms is READ if status is PRIVATE else True
                key = 'name' if type_ is FILE else 'title'
                yield get_test_name(**locals()), make, status, perms, type_, included, key


class TestGenerateCases(unittest.TestCase):

    # gc - generate_cases

    def test_gc_generates_cases(self):
        assert_equal(len(list(generate_cases())), 21)

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
    def test(self, ignored, make, status, perms, type_, included, key):
        node = make(status)

        auth = None
        if perms is not None:
            user = factories.AuthUserFactory()
            auth = user.auth
            if perms:
                node.add_contributor(user, perms)

        expected = [('Flim Flammity', type_)] if included else []
        results = self.results('flim', type_, auth)
        assert_equal([(x[key], x['category']) for x in results], expected)


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

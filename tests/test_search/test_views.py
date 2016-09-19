# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from nose.tools import *  # noqa PEP8 asserts
from nose_parameterized import parameterized

from tests import factories
from tests.base import DbIsolationMixin
from tests.test_search import OsfTestCase, SearchTestCase
from tests.utils import mock_archive
from website.project.model import Node
from website.util import api_url_for


class TestSearchPage(SearchTestCase):

    def test_search_projects(self):
        factories.ProjectFactory(title='Foo Bar')
        res = self.app.get('/search/', {'q': 'foo'})
        assert_equal(res.status_code, 200)


PRIVATE, PUBLIC = range(2)
PROJECT, REGISTRATION, COMPONENT, FILE = 'project registration component file'.split()
ANON, AUTH, READ = (None, '', 'r')
Y, N = True, False

cases = [
    ("private project hidden from anon", PRIVATE, PROJECT, ANON, N),
    ("private component hidden from anon", PRIVATE, COMPONENT, ANON, N),
    ("private file hidden from anon", PRIVATE, FILE, ANON, N),

    ("private project hidden from auth", PRIVATE, PROJECT, AUTH, N),
    ("private component hidden from auth", PRIVATE, COMPONENT, AUTH, N),
    ("private file hidden from auth", PRIVATE, FILE, AUTH, N),

    ("private project shown to read", PRIVATE, PROJECT, READ, Y),
    ("private component shown to read", PRIVATE, COMPONENT, READ, Y),
    ("private file shown to read", PRIVATE, FILE, READ, Y),


    ("public project shown to anon", PUBLIC, PROJECT, ANON, Y),
    ("public registration shown to anon", PUBLIC, REGISTRATION, ANON, Y),
    ("public component shown to anon", PUBLIC, COMPONENT, ANON, Y),
    ("public file shown to anon", PUBLIC, FILE, ANON, Y),

    ("public project shown to auth", PUBLIC, PROJECT, AUTH, Y),
    ("public registration shown to auth", PUBLIC, REGISTRATION, AUTH, Y),
    ("public component shown to auth", PUBLIC, COMPONENT, AUTH, Y),
    ("public file shown to auth", PUBLIC, FILE, AUTH, Y),

    ("public project shown to read", PUBLIC, PROJECT, READ, Y),
    ("public registration shown to read", PUBLIC, REGISTRATION, READ, Y),
    ("public component shown to read", PUBLIC, COMPONENT, READ, Y),
    ("public file shown to read", PUBLIC, FILE, READ, Y),
]

def make_project(status, user, perms):
    project = factories.ProjectFactory(title='Flim Flammity', is_public=status is PUBLIC)
    project.update_search()
    return 'title'

def make_registration(status, user, perms):
    project = factories.ProjectFactory(title='Flim Flammity', is_public=status is PUBLIC)
    mock_archive(project, autocomplete=True, autoapprove=True).__enter__()
    return 'title'

def make_component(status, user, perms):
    project = factories.ProjectFactory(title='Blim Blammity', is_public=status is PUBLIC)
    project.update_search()
    component = factories.NodeFactory(
        title='Flim Flammity',
        parent=project,
        is_public=status is PUBLIC,
    )
    component.update_search()
    return 'title'

def make_file(status, user, perms):
    project = factories.ProjectFactory(title='Blim Blammity', is_public=status is PUBLIC)
    project.get_addon('osfstorage').get_root().append_file('Flim Flammity')
    return 'name'

makers = {
    PROJECT: make_project,
    REGISTRATION: make_registration,
    COMPONENT: make_component,
    FILE: make_file,
}


class TestMakers(DbIsolationMixin, OsfTestCase):

    def test_there_are_no_nodes_to_start_with(self):
        assert Node.find().count() == 0


    # mp - make_project

    def test_mp_specifies_title(self):
        assert make_project('private', None, None) == 'title'

    def test_mp_makes_private_project_private(self):
        make_project(PRIVATE, None, None)
        assert not Node.find_one().is_public

    def test_mp_makes_public_project_public(self):
        make_project(PUBLIC, None, None)
        assert Node.find_one().is_public


    # mr - make_registration

    def test_mr_specifies_title(self):
        assert make_registration('private', None, None) == 'title'


    # mc - make_component

    def test_mc_specifies_title(self):
        assert make_component('private', None, None) == 'title'


    # mf - make_file

    def test_mf_specifies_name(self):
        assert make_file('private', None, None) == 'name'


class TestSearchSearchAPI(SearchTestCase):
    """Exercises the website.search.views.search_search view.
    """

    def results(self, query, category, auth):
        url = api_url_for('search_search')
        data = {'q': 'category:{} AND {}'.format(category, query)}
        return self.app.get(url, data, auth=auth).json['results']


    @parameterized.expand(cases)
    def test(self, ignored, status, type_, perms, included):
        user = None
        if perms is not None:
            user = factories.AuthUserFactory()

        make = makers[type_]
        key = make(status, user, perms)
        expected = [('Flim Flammity', type_)] if included else []
        results = self.results('flim', type_, user.auth if user else None)
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

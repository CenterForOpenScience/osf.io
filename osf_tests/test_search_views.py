# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

from nose.tools import *  # noqa PEP8 asserts

from osf_tests import factories
from tests.base import OsfTestCase
from website.util import api_url_for
from website.views import find_bookmark_collection


class TestSearchViews(OsfTestCase):

    def setUp(self):
        super(TestSearchViews, self).setUp()
        import website.search.search as search
        search.delete_all()

        robbie = factories.UserFactory(fullname='Robbie Williams')
        self.project = factories.ProjectFactory(creator=robbie)
        self.contrib = factories.UserFactory(fullname='Brian May')
        for i in range(0, 12):
            factories.UserFactory(fullname='Freddie Mercury{}'.format(i))

        self.user_one = factories.AuthUserFactory()
        self.user_two = factories.AuthUserFactory()
        self.project_private_user_one = factories.ProjectFactory(title='aaa', creator=self.user_one, is_public=False)
        self.project_private_user_two = factories.ProjectFactory(title='aaa', creator=self.user_two, is_public=False)
        self.project_public_user_one = factories.ProjectFactory(title='aaa', creator=self.user_one, is_public=True)
        self.project_public_user_two = factories.ProjectFactory(title='aaa', creator=self.user_two, is_public=True)

    def tearDown(self):
        super(TestSearchViews, self).tearDown()
        import website.search.search as search
        search.delete_all()

    def test_search_views(self):
        #Test search contributor
        url = api_url_for('search_contributor')
        res = self.app.get(url, {'query': self.contrib.fullname})
        assert_equal(res.status_code, 200)
        result = res.json['users']
        assert_equal(len(result), 1)
        brian = result[0]
        assert_equal(brian['fullname'], self.contrib.fullname)
        assert_in('profile_image_url', brian)
        assert_equal(brian['registered'], self.contrib.is_registered)
        assert_equal(brian['active'], self.contrib.is_active)

        #Test search pagination
        res = self.app.get(url, {'query': 'fr'})
        assert_equal(res.status_code, 200)
        result = res.json['users']
        pages = res.json['pages']
        page = res.json['page']
        assert_equal(len(result), 5)
        assert_equal(pages, 3)
        assert_equal(page, 0)

        #Test default page 1
        res = self.app.get(url, {'query': 'fr', 'page': 1})
        assert_equal(res.status_code, 200)
        result = res.json['users']
        page = res.json['page']
        assert_equal(len(result), 5)
        assert_equal(page, 1)

        #Test default page 2
        res = self.app.get(url, {'query': 'fr', 'page': 2})
        assert_equal(res.status_code, 200)
        result = res.json['users']
        page = res.json['page']
        assert_equal(len(result), 4)
        assert_equal(page, 2)

        #Test smaller pages
        res = self.app.get(url, {'query': 'fr', 'size': 5})
        assert_equal(res.status_code, 200)
        result = res.json['users']
        pages = res.json['pages']
        page = res.json['page']
        assert_equal(len(result), 5)
        assert_equal(page, 0)
        assert_equal(pages, 3)

        #Test smaller pages page 2
        res = self.app.get(url, {'query': 'fr', 'page': 2, 'size': 5, })
        assert_equal(res.status_code, 200)
        result = res.json['users']
        pages = res.json['pages']
        page = res.json['page']
        assert_equal(len(result), 4)
        assert_equal(page, 2)
        assert_equal(pages, 3)

        #Test search projects
        url = '/search/'
        res = self.app.get(url, {'q': self.project.title})
        assert_equal(res.status_code, 200)

        #Test search node
        res = self.app.post_json(
            api_url_for('search_node'),
            {'query': self.project.title},
            auth=factories.AuthUserFactory().auth
        )
        assert_equal(res.status_code, 200)

        #Test search node includePublic true
        res = self.app.post_json(
            api_url_for('search_node'),
            {'query': 'a', 'includePublic': True},
            auth=self.user_one.auth
        )
        node_ids = [node['id'] for node in res.json['nodes']]
        assert_in(self.project_private_user_one._id, node_ids)
        assert_in(self.project_public_user_one._id, node_ids)
        assert_in(self.project_public_user_two._id, node_ids)
        assert_not_in(self.project_private_user_two._id, node_ids)

        #Test search node includePublic false
        res = self.app.post_json(
            api_url_for('search_node'),
            {'query': 'a', 'includePublic': False},
            auth=self.user_one.auth
        )
        node_ids = [node['id'] for node in res.json['nodes']]
        assert_in(self.project_private_user_one._id, node_ids)
        assert_in(self.project_public_user_one._id, node_ids)
        assert_not_in(self.project_public_user_two._id, node_ids)
        assert_not_in(self.project_private_user_two._id, node_ids)

        #Test search user
        url = '/api/v1/search/user/'
        res = self.app.get(url, {'q': 'Umwali'})
        assert_equal(res.status_code, 200)
        assert_false(res.json['results'])

        user_one = factories.AuthUserFactory(fullname='Joe Umwali')
        user_two = factories.AuthUserFactory(fullname='Joan Uwase')

        res = self.app.get(url, {'q': 'Umwali'})

        assert_equal(res.status_code, 200)
        assert_equal(len(res.json['results']), 1)
        assert_false(res.json['results'][0]['social'])

        user_one.social = {
            'github': user_one.given_name,
            'twitter': user_one.given_name,
            'ssrn': user_one.given_name
        }
        user_one.save()

        res = self.app.get(url, {'q': 'Umwali'})

        assert_equal(res.status_code, 200)
        assert_equal(len(res.json['results']), 1)
        assert_not_in('Joan', res.body)
        assert_true(res.json['results'][0]['social'])
        assert_equal(res.json['results'][0]['names']['fullname'], user_one.fullname)
        assert_equal(res.json['results'][0]['social']['github'], 'http://github.com/{}'.format(user_one.given_name))
        assert_equal(res.json['results'][0]['social']['twitter'], 'http://twitter.com/{}'.format(user_one.given_name))
        assert_equal(res.json['results'][0]['social']['ssrn'], 'http://papers.ssrn.com/sol3/cf_dev/AbsByAuth.cfm?per_id={}'.format(user_one.given_name))

        user_two.social = {
            'profileWebsites': ['http://me.com/{}'.format(user_two.given_name)],
            'orcid': user_two.given_name,
            'linkedIn': user_two.given_name,
            'scholar': user_two.given_name,
            'impactStory': user_two.given_name,
            'baiduScholar': user_two.given_name
        }
        user_two.save()

        user_three = factories.AuthUserFactory(fullname='Janet Umwali')
        user_three.social = {
            'github': user_three.given_name,
            'ssrn': user_three.given_name
        }
        user_three.save()

        res = self.app.get(url, {'q': 'Umwali'})

        assert_equal(res.status_code, 200)
        assert_equal(len(res.json['results']), 2)
        assert_true(res.json['results'][0]['social'])
        assert_true(res.json['results'][1]['social'])
        assert_not_equal(res.json['results'][0]['social']['ssrn'], res.json['results'][1]['social']['ssrn'])
        assert_not_equal(res.json['results'][0]['social']['github'], res.json['results'][1]['social']['github'])

        res = self.app.get(url, {'q': 'Uwase'})

        assert_equal(res.status_code, 200)
        assert_equal(len(res.json['results']), 1)
        assert_true(res.json['results'][0]['social'])
        assert_not_in('ssrn', res.json['results'][0]['social'])
        assert_equal(res.json['results'][0]['social']['profileWebsites'][0], 'http://me.com/{}'.format(user_two.given_name))
        assert_equal(res.json['results'][0]['social']['impactStory'], 'https://impactstory.org/u/{}'.format(user_two.given_name))
        assert_equal(res.json['results'][0]['social']['orcid'], 'http://orcid.org/{}'.format(user_two.given_name))
        assert_equal(res.json['results'][0]['social']['baiduScholar'], 'http://xueshu.baidu.com/scholarID/{}'.format(user_two.given_name))
        assert_equal(res.json['results'][0]['social']['linkedIn'], 'https://www.linkedin.com/{}'.format(user_two.given_name))
        assert_equal(res.json['results'][0]['social']['scholar'], 'http://scholar.google.com/citations?user={}'.format(user_two.given_name))


class TestODMTitleSearch(OsfTestCase):
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
        super(TestODMTitleSearch, self).setUp()

        self.user = factories.AuthUserFactory()
        self.user_two = factories.AuthUserFactory()
        self.project = factories.ProjectFactory(creator=self.user, title='foo')
        self.project_two = factories.ProjectFactory(creator=self.user_two, title='bar')
        self.public_project = factories.ProjectFactory(creator=self.user_two, is_public=True, title='baz')
        self.registration_project = factories.RegistrationFactory(creator=self.user, title='qux')
        self.folder = factories.CollectionFactory(creator=self.user, title='quux')
        self.dashboard = find_bookmark_collection(self.user)
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
        assert_equal(res.status_code, 200)
        assert len(res.json) == 0
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
        assert_equal(res.status_code, 200)
        assert_equal(len(res.json), 0)

from os import environ
from unittest import mock

import pytest

from osf_tests import factories
from tests.base import OsfTestCase
from website.util import api_url_for
from website.views import find_bookmark_collection
from osf.external.spam import tasks as spam_tasks


@pytest.mark.enable_search
@pytest.mark.enable_enqueue_task
class TestSearchViews(OsfTestCase):

    def setUp(self):
        super().setUp()
        import website.search.search as search
        search.delete_all()

        robbie = factories.UserFactory(fullname='Robbie Williams')
        self.project = factories.ProjectFactory(creator=robbie)
        self.contrib = factories.UserFactory(fullname='Brian May')
        for i in range(0, 12):
            factories.UserFactory(fullname=f'Freddie Mercury{i}')

        self.user_one = factories.AuthUserFactory()
        self.user_two = factories.AuthUserFactory()
        self.project_private_user_one = factories.ProjectFactory(title='aaa', creator=self.user_one, is_public=False)
        self.project_private_user_two = factories.ProjectFactory(title='aaa', creator=self.user_two, is_public=False)
        self.project_public_user_one = factories.ProjectFactory(title='aaa', creator=self.user_one, is_public=True)
        self.project_public_user_two = factories.ProjectFactory(title='aaa', creator=self.user_two, is_public=True)

    def tearDown(self):
        super().tearDown()
        import website.search.search as search
        search.delete_all()

    # TODO: this might be failing b/c celery fails to propagate the changes to share
    # see https://github.com/CenterForOpenScience/osf.io/pull/10599
    @pytest.mark.skipif(
        not environ.get('CI'),
        reason="for some reason elasticsearch environment isn't properly set up locally, so this test passes only in CI"
    )
    def test_search_views(self):
        # Test search contributor
        url = api_url_for('search_contributor')
        res = self.app.get(url, query_string={'query': self.contrib.fullname})
        assert res.status_code == 200
        result = res.json['users']
        assert len(result) == 1
        brian = result[0]
        assert brian['fullname'] == self.contrib.fullname
        assert 'profile_image_url' in brian
        assert brian['registered'] == self.contrib.is_registered
        assert brian['active'] == self.contrib.is_active

        # Test search pagination
        res = self.app.get(url, query_string={'query': 'fr'})
        assert res.status_code == 200
        result = res.json['users']
        pages = res.json['pages']
        page = res.json['page']
        assert len(result) == 5
        assert pages == 3
        assert page == 0

        # Test default page 1
        res = self.app.get(url, query_string={'query': 'fr', 'page': 1})
        assert res.status_code == 200
        result = res.json['users']
        page = res.json['page']
        assert len(result) == 5
        assert page == 1

        # Test default page 2
        res = self.app.get(url, query_string={'query': 'fr', 'page': 2})
        assert res.status_code == 200
        result = res.json['users']
        page = res.json['page']
        assert len(result) == 4
        assert page == 2

        # Test smaller pages
        res = self.app.get(url, query_string={'query': 'fr', 'size': 5})
        assert res.status_code == 200
        result = res.json['users']
        pages = res.json['pages']
        page = res.json['page']
        assert len(result) == 5
        assert page == 0
        assert pages == 3

        # Test smaller pages page 2
        res = self.app.get(url, query_string={'query': 'fr', 'size': 5, 'page': 2})
        assert res.status_code == 200
        result = res.json['users']
        pages = res.json['pages']
        page = res.json['page']
        assert len(result) == 4
        assert page == 2
        assert pages == 3

        # Test search projects
        url = '/search/'
        res = self.app.get(url, query_string={'q': self.project.title})
        assert res.status_code == 200

        # Test search node
        res = self.app.post(
            api_url_for('search_node'),
            json={'query': self.project.title},
            auth=factories.AuthUserFactory().auth
        )
        assert res.status_code == 200

        # Test search node includePublic true
        res = self.app.post(
            api_url_for('search_node'),
            json={'query': 'a', 'includePublic': True},
            auth=self.user_one.auth
        )
        node_ids = [node['id'] for node in res.json['nodes']]
        assert self.project_private_user_one._id in node_ids
        assert self.project_public_user_one._id in node_ids
        assert self.project_public_user_two._id in node_ids
        assert self.project_private_user_two._id not in node_ids

        # Test search node includePublic false
        res = self.app.post(
            api_url_for('search_node'),
            json={'query': 'a', 'includePublic': False},
            auth=self.user_one.auth
        )
        node_ids = [node['id'] for node in res.json['nodes']]
        assert self.project_private_user_one._id in node_ids
        assert self.project_public_user_one._id in node_ids
        assert self.project_public_user_two._id not in node_ids
        assert self.project_private_user_two._id not in node_ids

        # Test search user
        url = '/api/v1/search/user/'
        res = self.app.get(url, query_string={'q': 'Umwali'})
        assert res.status_code == 200
        assert not res.json['results']

        user_one = factories.AuthUserFactory(fullname='Joe Umwali')
        user_two = factories.AuthUserFactory(fullname='Joan Uwase')

        res = self.app.get(url, query_string={'q': 'Umwali'})

        assert res.status_code == 200
        assert len(res.json['results']) == 1
        assert not res.json['results'][0]['social']

        user_one.social = {
            'github': user_one.given_name,
            'twitter': user_one.given_name,
            'ssrn': user_one.given_name
        }
        user_one.save()

        res = self.app.get(url, query_string={'q': 'Umwali'})

        assert res.status_code == 200
        assert len(res.json['results']) == 1
        assert 'Joan' not in res.text
        assert res.json['results'][0]['social']
        assert res.json['results'][0]['names']['fullname'] == user_one.fullname
        assert res.json['results'][0]['social']['github'] == f'http://github.com/{user_one.given_name}'
        assert res.json['results'][0]['social']['twitter'] == f'http://twitter.com/{user_one.given_name}'
        assert res.json['results'][0]['social']['ssrn'] == f'http://papers.ssrn.com/sol3/cf_dev/AbsByAuth.cfm?per_id={user_one.given_name}'

        user_two.social = {
            'profileWebsites': [f'http://me.com/{user_two.given_name}'],
            'orcid': user_two.given_name,
            'linkedIn': user_two.given_name,
            'scholar': user_two.given_name,
            'impactStory': user_two.given_name,
            'baiduScholar': user_two.given_name
        }
        with mock.patch.object(spam_tasks.requests, 'head'):
            user_two.save()

        user_three = factories.AuthUserFactory(fullname='Janet Umwali')
        user_three.social = {
            'github': user_three.given_name,
            'ssrn': user_three.given_name
        }
        user_three.save()

        res = self.app.get(url, query_string={'q': 'Umwali'})

        assert res.status_code == 200
        assert len(res.json['results']) == 2
        assert res.json['results'][0]['social']
        assert res.json['results'][1]['social']
        assert res.json['results'][0]['social']['ssrn'] != res.json['results'][1]['social']['ssrn']
        assert res.json['results'][0]['social']['github'] != res.json['results'][1]['social']['github']

        res = self.app.get(url, query_string={'q': 'Uwase'})

        assert res.status_code == 200
        assert len(res.json['results']) == 1
        assert res.json['results'][0]['social']
        assert 'ssrn' not in res.json['results'][0]['social']
        assert res.json['results'][0]['social']['profileWebsites'][0] == f'http://me.com/{user_two.given_name}'
        assert res.json['results'][0]['social']['impactStory'] == f'https://impactstory.org/u/{user_two.given_name}'
        assert res.json['results'][0]['social']['orcid'] == f'http://orcid.org/{user_two.given_name}'
        assert res.json['results'][0]['social']['baiduScholar'] == f'http://xueshu.baidu.com/scholarID/{user_two.given_name}'
        assert res.json['results'][0]['social']['linkedIn'] == f'https://www.linkedin.com/{user_two.given_name}'
        assert res.json['results'][0]['social']['scholar'] == f'http://scholar.google.com/citations?user={user_two.given_name}'


@pytest.mark.enable_bookmark_creation
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
        super().setUp()

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
        res = self.app.get(self.url, query_string={'term': self.project.title}, auth=self.user.auth)
        assert res.status_code == 200
        assert len(res.json) == 1
        res = self.app.get(self.url,
                           query_string={
                               'term': self.public_project.title,
                               'includePublic': 'yes',
                               'includeContributed': 'no'
                           }, auth=self.user.auth)
        assert res.status_code == 200
        assert len(res.json) == 1
        res = self.app.get(self.url,
                           query_string={
                               'term': self.project.title,
                               'includePublic': 'no',
                               'includeContributed': 'yes'
                           }, auth=self.user.auth)
        assert res.status_code == 200
        assert len(res.json) == 1
        res = self.app.get(self.url,
                           query_string={
                               'term': self.project.title,
                               'includePublic': 'no',
                               'includeContributed': 'yes',
                               'isRegistration': 'no'
                           }, auth=self.user.auth)
        assert res.status_code == 200
        assert len(res.json) == 1
        res = self.app.get(self.url,
                           query_string={
                               'term': self.project.title,
                               'includePublic': 'yes',
                               'includeContributed': 'yes',
                               'isRegistration': 'either'
                           }, auth=self.user.auth)
        assert res.status_code == 200
        assert len(res.json) == 1
        res = self.app.get(self.url,
                           query_string={
                               'term': self.public_project.title,
                               'includePublic': 'yes',
                               'includeContributed': 'yes',
                               'isRegistration': 'either'
                           }, auth=self.user.auth)
        assert res.status_code == 200
        assert len(res.json) == 1
        res = self.app.get(self.url,
                           query_string={
                               'term': self.registration_project.title,
                               'includePublic': 'yes',
                               'includeContributed': 'yes',
                               'isRegistration': 'either'
                           }, auth=self.user.auth)
        assert res.status_code == 200
        assert len(res.json) == 2
        res = self.app.get(self.url,
                           query_string={
                               'term': self.registration_project.title,
                               'includePublic': 'yes',
                               'includeContributed': 'yes',
                               'isRegistration': 'no'
                           }, auth=self.user.auth)
        assert res.status_code == 200
        assert len(res.json) == 1
        res = self.app.get(self.url,
                           query_string={
                               'term': self.folder.title,
                               'includePublic': 'yes',
                               'includeContributed': 'yes',
                               'isFolder': 'yes'
                           }, auth=self.user.auth)
        assert res.status_code == 200
        assert len(res.json) == 0
        res = self.app.get(self.url,
                           query_string={
                               'term': self.folder.title,
                               'includePublic': 'yes',
                               'includeContributed': 'yes',
                               'isFolder': 'no'
                           }, auth=self.user.auth)
        assert res.status_code == 200
        assert len(res.json) == 0
        res = self.app.get(self.url,
                           query_string={
                               'term': self.dashboard.title,
                               'includePublic': 'yes',
                               'includeContributed': 'yes',
                               'isFolder': 'no'
                           }, auth=self.user.auth)
        assert res.status_code == 200
        assert len(res.json) == 0
        res = self.app.get(self.url,
                           query_string={
                               'term': self.dashboard.title,
                               'includePublic': 'yes',
                               'includeContributed': 'yes',
                               'isFolder': 'yes'
                           }, auth=self.user.auth)
        assert res.status_code == 200
        assert len(res.json) == 0

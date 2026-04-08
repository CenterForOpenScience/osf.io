from os import environ
from unittest import mock

import pytest

from osf_tests import factories
from tests.base import OsfTestCase
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

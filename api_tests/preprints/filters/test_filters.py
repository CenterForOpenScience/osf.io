# -*- coding: utf-8 -*-
import pytest

from framework.auth.core import Auth
from tests.json_api_test_app import JSONAPITestApp
from osf_tests.factories import (
    PreprintFactory,
    AuthUserFactory,
    SubjectFactory,
    PreprintProviderFactory
)

@pytest.mark.django_db
class PreprintsListFilteringMixin(object):

    # FIXTURES

    @pytest.fixture()
    def user(self):
        raise NotImplementedError("subclass must define a user fixture")

    @pytest.fixture()
    def provider_one(self):
        raise NotImplementedError("subclass must define a provider_one fixture")

    @pytest.fixture()
    def provider_two(self):
        raise NotImplementedError("subclass must define a provider_two fixture")

    @pytest.fixture()
    def provider_three(self):
        raise NotImplementedError("subclass must define a provider_three fixture")

    @pytest.fixture()
    def project_one(self):
        raise NotImplementedError("subclass must define a project_one fixture")

    @pytest.fixture()
    def project_two(self):
        raise NotImplementedError("subclass must define a project_two fixture")

    @pytest.fixture()
    def project_three(self):
        raise NotImplementedError("subclass must define a project_three fixture")

    @pytest.fixture()
    def url(self):
        raise NotImplementedError("subclass must define a url fixture")

    @pytest.fixture()
    def app(self):
        return JSONAPITestApp()

    @pytest.fixture()
    def subject_one(self):
        return SubjectFactory(text='First Subject')

    @pytest.fixture()
    def subject_two(self):
        return SubjectFactory(text='Second Subject')

    # SETUP

    @pytest.fixture(scope="function", autouse=True)
    def int(self, user, provider_one, provider_two, provider_three, project_one, project_two, project_three, url, app, subject_one, subject_two):
        self.user = user
        self.provider_one = provider_one
        self.provider_two = provider_two
        self.provider_three = provider_three
        self.project_one = project_one
        self.project_two = project_two
        self.project_three = project_three
        self.url = url
        self.app = app
        self.subject_one = subject_one
        self.subject_two = subject_two

        self.preprint_one = PreprintFactory(creator=self.user, project=self.project_one, provider=self.provider_one, subjects=[[self.subject_one._id]])
        self.preprint_two = PreprintFactory(creator=self.user, project=self.project_two, filename='tough.txt', provider=self.provider_two, subjects=[[self.subject_two._id]])
        self.preprint_three = PreprintFactory(creator=self.user, project=self.project_three, filename='darn.txt', provider=self.provider_three, subjects=[[self.subject_one._id], [self.subject_two._id]])

        self.preprint_two.date_created = '2013-12-11 10:09:08.070605+00:00'
        self.preprint_two.date_published = '2013-12-11 10:09:08.070605+00:00'
        self.preprint_two.save()

        self.preprint_three.date_created = '2013-12-11 10:09:08.070605+00:00'
        self.preprint_three.date_published = '2013-12-11 10:09:08.070605+00:00'
        self.preprint_three.is_published = False
        self.preprint_three.save()

        self.provider_url = '{}filter[provider]='.format(self.url)
        self.id_url = '{}filter[id]='.format(self.url)
        self.date_created_url = '{}filter[date_created]='.format(self.url)
        self.date_modified_url = '{}filter[date_modified]='.format(self.url)
        self.date_published_url = '{}filter[date_published]='.format(self.url)
        self.is_published_url = '{}filter[is_published]='.format(self.url)

        self.is_published_and_modified_url = '{}filter[is_published]=true&filter[date_created]=2013-12-11'.format(self.url)

        self.has_subject = '{}filter[subjects]='.format(self.url)

    # TESTS

    def test_provider_filter_null(self):
        expected = []
        res = self.app.get('{}null'.format(self.provider_url), auth=self.user.auth)
        actual = [preprint['id'] for preprint in res.json['data']]
        assert expected == actual

    def test_id_filter_null(self):
        expected = []
        res = self.app.get('{}null'.format(self.id_url), auth=self.user.auth)
        actual = [preprint['id'] for preprint in res.json['data']]
        assert expected == actual

    def test_id_filter_equals_returns_one(self):
        expected = [self.preprint_two._id]
        res = self.app.get('{}{}'.format(self.id_url, self.preprint_two._id), auth=self.user.auth)
        actual = [preprint['id'] for preprint in res.json['data']]
        assert expected == actual

    def test_date_created_filter_equals_returns_none(self):
        expected = []
        res = self.app.get('{}{}'.format(self.date_created_url, '2015-11-15 10:09:08.070605+00:00'), auth=self.user.auth)
        actual = [preprint['id'] for preprint in res.json['data']]
        assert expected == actual

    def test_date_created_filter_equals_returns_one(self):
        expected = [self.preprint_one._id]
        res = self.app.get('{}{}'.format(self.date_created_url, self.preprint_one.date_created), auth=self.user.auth)
        actual = [preprint['id'] for preprint in res.json['data']]
        assert expected == actual

    def test_date_created_filter_equals_returns_multiple(self):
        expected = set([self.preprint_two._id, self.preprint_three._id])
        res = self.app.get('{}{}'.format(self.date_created_url, self.preprint_two.date_created), auth=self.user.auth)
        actual = set([preprint['id'] for preprint in res.json['data']])
        assert expected == actual

    def test_date_modified_filter_equals_returns_none(self):
        expected = []
        res = self.app.get('{}{}'.format(self.date_modified_url, '2015-11-15 10:09:08.070605+00:00'), auth=self.user.auth)
        actual = [preprint['id'] for preprint in res.json['data']]
        assert expected == actual

    # This test was causing problems because modifying anything caused set modified dates to update to current date
    # This test could hypothetically fail if the time between fixture creations splits a day (e.g., midnight)
    def test_date_modified_filter_equals_returns_multiple(self):
        expected = set([self.preprint_one._id, self.preprint_two._id, self.preprint_three._id])
        res = self.app.get('{}{}'.format(self.date_modified_url, self.preprint_one.date_modified), auth=self.user.auth)
        actual = set([preprint['id'] for preprint in res.json['data']])
        assert expected == actual

    def test_date_published_filter_equals_returns_none(self):
        expected = []
        res = self.app.get('{}{}'.format(self.date_published_url, '2015-11-15 10:09:08.070605+00:00'), auth=self.user.auth)
        actual = [preprint['id'] for preprint in res.json['data']]
        assert expected == actual

    def test_date_published_filter_equals_returns_one(self):
        expected = [self.preprint_one._id]
        res = self.app.get('{}{}'.format(self.date_published_url, self.preprint_one.date_published), auth=self.user.auth)
        actual = [preprint['id'] for preprint in res.json['data']]
        assert expected == actual

    def test_date_published_filter_equals_returns_multiple(self):
        expected = set([self.preprint_two._id, self.preprint_three._id])
        res = self.app.get('{}{}'.format(self.date_published_url, self.preprint_two.date_published), auth=self.user.auth)
        actual = set([preprint['id'] for preprint in res.json['data']])
        assert expected == actual

    def test_is_published_false_filter_equals_returns_one(self):
        expected = [self.preprint_three._id]
        res = self.app.get('{}{}'.format(self.is_published_url, 'false'), auth=self.user.auth)
        actual = [preprint['id'] for preprint in res.json['data']]
        assert expected == actual

    def test_is_published_true_filter_equals_returns_multiple(self):
        expected = set([self.preprint_one._id, self.preprint_two._id])
        res = self.app.get('{}{}'.format(self.is_published_url, 'true'), auth=self.user.auth)
        actual = set([preprint['id'] for preprint in res.json['data']])
        assert expected == actual

    def test_multiple_filters_returns_one(self):
        expected = set([self.preprint_two._id])
        res = self.app.get(self.is_published_and_modified_url,
            auth=self.user.auth
        )
        actual = set([preprint['id'] for preprint in res.json['data']])
        assert expected == actual

    def test_subject_filter_using_id(self):
        expected = set([self.preprint_one._id, self.preprint_three._id])
        res = self.app.get('{}{}'.format(self.has_subject, self.subject_one._id),
            auth=self.user.auth
        )
        actual = set([preprint['id'] for preprint in res.json['data']])
        assert expected == actual

    def test_subject_filter_using_text(self):
        expected = set([self.preprint_one._id, self.preprint_three._id])
        res = self.app.get('{}{}'.format(self.has_subject, self.subject_one.text),
            auth=self.user.auth
        )
        actual = set([preprint['id'] for preprint in res.json['data']])
        assert expected == actual

    def test_unknows_subject_filter(self):
        res = self.app.get('{}notActuallyASubjectIdOrTestMostLikely'.format(self.has_subject),
            auth=self.user.auth
        )
        assert len(res.json['data']) == 0

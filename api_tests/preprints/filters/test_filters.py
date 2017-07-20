import pytest

from framework.auth.core import Auth
from osf_tests.factories import (
    PreprintFactory,
    AuthUserFactory,
    SubjectFactory,
    PreprintProviderFactory
)

@pytest.mark.django_db
class PreprintsListFilteringMixin(object):

    @pytest.fixture()
    def user(self):
        raise NotImplementedError

    @pytest.fixture()
    def provider_one(self):
        raise NotImplementedError

    @pytest.fixture()
    def provider_two(self):
        raise NotImplementedError

    @pytest.fixture()
    def provider_three(self):
        raise NotImplementedError

    @pytest.fixture()
    def project_one(self):
        raise NotImplementedError

    @pytest.fixture()
    def project_two(self):
        raise NotImplementedError

    @pytest.fixture()
    def project_three(self):
        raise NotImplementedError

    @pytest.fixture()
    def url(self):
        raise NotImplementedError

    @pytest.fixture()
    def subject_one(self):
        return SubjectFactory(text='First Subject')

    @pytest.fixture()
    def subject_two(self):
        return SubjectFactory(text='Second Subject')

    @pytest.fixture()
    def preprint_one(self, user, project_one, provider_one, subject_one):
        return PreprintFactory(creator=user, project=project_one, provider=provider_one, subjects=[[subject_one._id]])

    @pytest.fixture()
    def preprint_two(self, user, project_two, provider_two, subject_two):
        preprint_two = PreprintFactory(creator=user, project=project_two, filename='howto_reason.txt', provider=provider_two, subjects=[[subject_two._id]])
        preprint_two.date_created = '2013-12-11 10:09:08.070605+00:00'
        preprint_two.date_published = '2013-12-11 10:09:08.070605+00:00'
        preprint_two.save()
        return preprint_two

    @pytest.fixture()
    def preprint_three(self, user, project_three, provider_three, subject_one, subject_two):
        preprint_three = PreprintFactory(creator=user, project=project_three, filename='darn_reason.txt', provider=provider_three, subjects=[[subject_one._id], [subject_two._id]])
        preprint_three.date_created = '2013-12-11 10:09:08.070605+00:00'
        preprint_three.date_published = '2013-12-11 10:09:08.070605+00:00'
        preprint_three.is_published = False
        preprint_three.save()
        return preprint_three


    @pytest.fixture()
    def provider_url(self, url):
        return '{}filter[provider]='.format(url)

    @pytest.fixture()
    def id_url(self, url):
        return '{}filter[id]='.format(url)

    @pytest.fixture()
    def date_created_url(self, url):
        return '{}filter[date_created]='.format(url)

    @pytest.fixture()
    def date_modified_url(self, url):
        return '{}filter[date_modified]='.format(url)

    @pytest.fixture()
    def date_published_url(self, url):
        return '{}filter[date_published]='.format(url)

    @pytest.fixture()
    def is_published_url(self, url):
        return '{}filter[is_published]='.format(url)

    @pytest.fixture()
    def is_published_and_modified_url(self, url):
        return '{}filter[is_published]=true&filter[date_created]=2013-12-11'.format(url)

    @pytest.fixture()
    def has_subject(self, url):
        return '{}filter[subjects]='.format(url)

    def test_provider_filter_null(self, app, user, provider_url):
        expected = []
        res = app.get('{}null'.format(provider_url), auth=user.auth)
        actual = [preprint['id'] for preprint in res.json['data']]
        assert expected == actual

    def test_id_filter_null(self, app, user, id_url):
        expected = []
        res = app.get('{}null'.format(id_url), auth=user.auth)
        actual = [preprint['id'] for preprint in res.json['data']]
        assert expected == actual

    def test_id_filter_equals_returns_one(self, app, user, preprint_two, id_url):
        expected = [preprint_two._id]
        res = app.get('{}{}'.format(id_url, preprint_two._id), auth=user.auth)
        actual = [preprint['id'] for preprint in res.json['data']]
        assert expected == actual

    def test_date_created_filter_equals_returns_none(self, app, user, date_created_url):
        expected = []
        res = app.get('{}{}'.format(date_created_url, '2015-11-15 10:09:08.070605+00:00'), auth=user.auth)
        actual = [preprint['id'] for preprint in res.json['data']]
        assert expected == actual

    def test_date_created_filter_equals_returns_one(self, app, user, preprint_one, date_created_url):
        expected = [preprint_one._id]
        res = app.get('{}{}'.format(date_created_url, preprint_one.date_created), auth=user.auth)
        actual = [preprint['id'] for preprint in res.json['data']]
        assert expected == actual

    def test_date_created_filter_equals_returns_multiple(self, app, user, preprint_two, preprint_three, date_created_url):
        expected = set([preprint_two._id, preprint_three._id])
        res = app.get('{}{}'.format(date_created_url, preprint_two.date_created), auth=user.auth)
        actual = set([preprint['id'] for preprint in res.json['data']])
        assert expected == actual

    def test_date_modified_filter_equals_returns_none(self, app, user, date_modified_url):
        expected = []
        res = app.get('{}{}'.format(date_modified_url, '2015-11-15 10:09:08.070605+00:00'), auth=user.auth)
        actual = [preprint['id'] for preprint in res.json['data']]
        assert expected == actual

    # This test was causing problems because modifying anything caused set modified dates to update to current date
    # This test could hypothetically fail if the time between fixture creations splits a day (e.g., midnight)
    def test_date_modified_filter_equals_returns_multiple(self, app, user, preprint_one, preprint_two, preprint_three, date_modified_url):
        expected = set([preprint_one._id, preprint_two._id, preprint_three._id])
        res = app.get('{}{}'.format(date_modified_url, preprint_one.date_modified), auth=user.auth)
        actual = set([preprint['id'] for preprint in res.json['data']])
        assert expected == actual

    def test_date_published_filter_equals_returns_none(self, app, user, date_published_url):
        expected = []
        res = app.get('{}{}'.format(date_published_url, '2015-11-15 10:09:08.070605+00:00'), auth=user.auth)
        actual = [preprint['id'] for preprint in res.json['data']]
        assert expected == actual

    def test_date_published_filter_equals_returns_one(self, app, user, preprint_one, date_published_url):
        expected = [preprint_one._id]
        res = app.get('{}{}'.format(date_published_url, preprint_one.date_published), auth=user.auth)
        actual = [preprint['id'] for preprint in res.json['data']]
        assert expected == actual

    def test_date_published_filter_equals_returns_multiple(self, app, user, preprint_two, preprint_three, date_published_url):
        expected = set([preprint_two._id, preprint_three._id])
        res = app.get('{}{}'.format(date_published_url, preprint_two.date_published), auth=user.auth)
        actual = set([preprint['id'] for preprint in res.json['data']])
        assert expected == actual

    def test_is_published_false_filter_equals_returns_one(self, app, user, preprint_three, is_published_url):
        expected = [preprint_three._id]
        res = app.get('{}{}'.format(is_published_url, 'false'), auth=user.auth)
        actual = [preprint['id'] for preprint in res.json['data']]
        assert expected == actual

    def test_is_published_true_filter_equals_returns_multiple(self, app, user, preprint_one, preprint_two, is_published_url):
        expected = set([preprint_one._id, preprint_two._id])
        res = app.get('{}{}'.format(is_published_url, 'true'), auth=user.auth)
        actual = set([preprint['id'] for preprint in res.json['data']])
        assert expected == actual

    def test_multiple_filters_returns_one(self, app, user, preprint_two, is_published_and_modified_url):
        expected = set([preprint_two._id])
        res = app.get(is_published_and_modified_url,
            auth=user.auth
        )
        actual = set([preprint['id'] for preprint in res.json['data']])
        assert expected == actual

    def test_subject_filter_using_id(self, app, user, subject_one, preprint_one, preprint_three, has_subject):
        expected = set([preprint_one._id, preprint_three._id])
        res = app.get('{}{}'.format(has_subject, subject_one._id),
            auth=user.auth
        )
        actual = set([preprint['id'] for preprint in res.json['data']])
        assert expected == actual

    def test_subject_filter_using_text(self, app, user, subject_one, preprint_one, preprint_three, has_subject):
        expected = set([preprint_one._id, preprint_three._id])
        res = app.get('{}{}'.format(has_subject, subject_one.text),
            auth=user.auth
        )
        actual = set([preprint['id'] for preprint in res.json['data']])
        assert expected == actual

    def test_unknows_subject_filter(self, app, user, has_subject):
        res = app.get('{}notActuallyASubjectIdOrTestMostLikely'.format(has_subject),
            auth=user.auth
        )
        assert len(res.json['data']) == 0

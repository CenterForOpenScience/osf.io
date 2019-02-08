import pytest

from api.base.settings import API_BASE
from osf_tests.factories import EducationFactory, AuthUserFactory


@pytest.fixture
def user():
    return AuthUserFactory()

@pytest.fixture
def user_two():
    return AuthUserFactory()

@pytest.fixture
def education_one(user):
    return EducationFactory(user=user, institution='Edu One')

@pytest.fixture
def education_two(user):
    return EducationFactory(user=user, institution='Edu Two')


@pytest.fixture
def url_one(user, education_one):
    return


@pytest.mark.django_db
class TestEducation:

    def test_get_education_list_get(self, app, user, user_two, education_one, education_two):
        url = '/{}education/'.format(API_BASE)

        # unauthorized can access
        res = app.get(url)
        assert res.status_code == 200

        # another authorized user can access
        res = app.get(url, auth=user_two.auth)
        assert res.status_code == 200

        # authorized can access self
        res = app.get(url, auth=user.auth)
        assert res.status_code == 200

        ids = [result['id'] for result in res.json['data']]
        assert education_one._id in ids
        assert education_two._id in ids

        # self link is the user education detail view
        first = res.json['data'][0]
        assert 'users/{}/education/{}'.format(user._id, education_one._id) in first['links']['self']

    def test_filter_education_list(self, app, user, education_one, education_two):
        education_one_two = EducationFactory(user=user, institution='Edu One')
        education_two_two = EducationFactory(user=user, institution='Edu Two')

        # filter by institution
        url = '/{}education/?filter[institution]=Edu One'.format(API_BASE)
        res = app.get(url)

        ids = [result['id'] for result in res.json['data']]
        assert education_one._id in ids
        assert education_one_two._id in ids
        assert education_two._id not in ids
        assert education_two_two._id not in ids

import pytest

from api.base.settings import API_BASE
from osf_tests.factories import UserEmploymentFactory, AuthUserFactory


@pytest.fixture
def user():
    return AuthUserFactory()

@pytest.fixture
def user_two():
    return AuthUserFactory()

@pytest.fixture
def employment_one(user):
    return UserEmploymentFactory(user=user, institution='Employment One')

@pytest.fixture
def employment_two(user):
    return UserEmploymentFactory(user=user, institution='Employment Two')


@pytest.fixture
def url_one(user, employment_one):
    return '/{}employment/{}/'.format(API_BASE, employment_one._id)


@pytest.mark.django_db
class TestEmployment:

    def test_get_employment_list_get(self, app, user, user_two, employment_one, employment_two):
        url = '/{}employment/'.format(API_BASE)

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
        assert employment_one._id in ids
        assert employment_two._id in ids

        # self link is the user employment detail view
        first = res.json['data'][0]
        assert 'users/{}/employment/{}'.format(user._id, employment_one._id) in first['links']['self']

    def test_filter_employment_list(self, app, user, employment_one, employment_two):
        employment_one_two = UserEmploymentFactory(user=user, institution='Employment One')
        employment_two_two = UserEmploymentFactory(user=user, institution='Employment Two')

        # filter by institution
        url = '/{}employment/?filter[institution]=Employment One'.format(API_BASE)
        res = app.get(url)

        ids = [result['id'] for result in res.json['data']]
        assert employment_one._id in ids
        assert employment_one_two._id in ids
        assert employment_two._id not in ids
        assert employment_two_two._id not in ids

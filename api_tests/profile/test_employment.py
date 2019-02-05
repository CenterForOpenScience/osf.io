import pytest

from api.base.settings import API_BASE
from osf_tests.factories import EmploymentFactory, AuthUserFactory


@pytest.fixture
def user():
    return AuthUserFactory()

@pytest.fixture
def user_two():
    return AuthUserFactory()

@pytest.fixture
def employment_one(user):
    return EmploymentFactory(user=user)

@pytest.fixture
def employment_two(user):
    return EmploymentFactory(user=user)


@pytest.fixture
def url_one(user, employment_one):
    return '/{}employment/{}/'.format(API_BASE, employment_one._id)


@pytest.mark.django_db
class TestEmployment:

    def test_get_employment_detail(self, app, user, url_one, employment_one):
        # unauthoized can access
        res = app.get(url_one)
        assert res.status_code == 200

        # another authorized user can access
        other_user = AuthUserFactory()
        res = app.get(url_one, auth=other_user.auth)
        assert res.status_code == 200

        # authorized can access self
        res = app.get(url_one, auth=user.auth)
        assert res.status_code == 200

    def test_get_employment_list_get(self, app, user):
        pass   # TODO
        # unauthorized can access

        # another authorized user can access

    def test_filter_employment_list(self, app, user):
        pass  # TODO

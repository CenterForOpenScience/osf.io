import pytest

from osf_tests.factories import AuthUserFactory, InstitutionFactory


@pytest.mark.django_db
class TestUserInstitutions:
    @pytest.fixture()
    def institutions(self):
        return InstitutionFactory(), InstitutionFactory()

    @pytest.fixture()
    def user(self, institutions):
        user = AuthUserFactory()
        for each in institutions:
            user.affiliated_institutions.add(each)
        return user

    @pytest.fixture()
    def user_institutions_url(self, user):
        return '/v2/users/{}/institutions/'.format(user._id)

    def test_get_success(self, app, user, user_institutions_url):
        res = app.get(user_institutions_url)
        assert res.status_code == 200
        assert len(res.json['data']) == user.affiliated_institutions.count()

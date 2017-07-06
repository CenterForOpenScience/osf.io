import pytest

from api.base.settings.defaults import API_BASE
from osf_tests.factories import (
    InstitutionFactory,
    UserFactory,
)

@pytest.mark.django_db
class TestInstitutionUsersList:

    @pytest.fixture()
    def institution(self):
        return InstitutionFactory()

    @pytest.fixture()
    def user_one(self, institution):
        user_one = UserFactory()
        user_one.affiliated_institutions.add(institution)
        user_one.save()
        return user_one

    @pytest.fixture()
    def user_two(self, institution):
        user_two = UserFactory()
        user_two.affiliated_institutions.add(institution)
        user_two.save()
        return user_two

    @pytest.fixture()
    def url_institution_user(self, institution):
        return '/{0}institutions/{1}/users/'.format(API_BASE, institution._id)

    def test_return_all_users(self, app, institution, user_one, user_two, url_institution_user):
        res = app.get(url_institution_user)

        assert res.status_code == 200

        ids = [each['id'] for each in res.json['data']]
        assert len(res.json['data']) == 2
        assert user_one._id in ids
        assert user_two._id in ids

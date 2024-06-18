import pytest

from api.base.settings.defaults import API_BASE
from osf_tests.factories import (
    InstitutionFactory,
    AuthUserFactory,
)


@pytest.mark.django_db
@pytest.mark.enable_quickfiles_creation
class TestInstitutionUsersList:

    def test_return_all_users(self, app):
        institution = InstitutionFactory()

        user_one = AuthUserFactory()
        user_one.affiliated_institutions.add(institution)
        user_one.save()

        user_two = AuthUserFactory()
        user_two.affiliated_institutions.add(institution)
        user_two.save()

        url = '/{0}institutions/{1}/users/'.format(API_BASE, institution._id)
        res = app.get(url, auth=user_one.auth, expect_errors=True)

        assert res.status_code == 403

    def test_return_all_users_not_logged_in(self, app):
        institution = InstitutionFactory()

        user_one = AuthUserFactory()
        user_one.affiliated_institutions.add(institution)
        user_one.save()

        user_two = AuthUserFactory()
        user_two.affiliated_institutions.add(institution)
        user_two.save()

        url = '/{0}institutions/{1}/users/'.format(API_BASE, institution._id)
        res = app.get(url, expect_errors=True)

        assert res.status_code == 401

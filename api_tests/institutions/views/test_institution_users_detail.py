from nose.tools import *  # flake8: noqa

from tests.base import ApiTestCase
from tests.factories import InstitutionFactory, AuthUserFactory

from api.base.settings.defaults import API_BASE

class TestInstitutionUsersList(ApiTestCase):
    def setUp(self):
        super(TestInstitutionUsersList, self).setUp()
        self.institution = InstitutionFactory()
        self.user = AuthUserFactory()
        self.user.affiliated_institutions.append(self.institution)
        self.user.save()
        self.user2 = AuthUserFactory()

        self.institution_users_url = '/{0}institutions/{1}/users/'.format(API_BASE, self.institution._id)

    def test_return_user_wrong_id(self):
        url = self.institution_users_url + self.user2._id + '/'
        res = self.app.get(url, expect_errors=True)

        assert_equal(res.status_code, 404)

    def test_return_user_with_id(self):
        url = self.institution_users_url + self.user._id + '/'
        res = self.app.get(url)

        assert_equal(res.status_code, 200)
        assert_equal(self.user.fullname, res.json['data']['attributes']['full_name'])
        assert_equal(self.user._id, res.json['data']['id'])


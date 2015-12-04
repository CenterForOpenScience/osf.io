from nose.tools import *

from tests.base import ApiTestCase
from tests.factories import InstitutionFactory, UserFactory

from api.base.settings.defaults import API_BASE

class TestInstitutionUsersList(ApiTestCase):
    def setUp(self):
        super(TestInstitutionUsersList, self).setUp()
        self.institution = InstitutionFactory()
        self.user1 = UserFactory()
        self.user1.affiliated_institutions.append(self.institution)
        self.user1.save()
        self.user2 = UserFactory()
        self.user2.affiliated_institutions.append(self.institution)
        self.user2.save()

        self.institution_user_url = '/{0}institutions/{1}/users/'.format(API_BASE, self.institution._id)

    def test_return_all_users(self):
        res = self.app.get(self.institution_user_url)

        assert_equal(res.status_code, 200)
        assert_equal(len(res.json['data']), 2)

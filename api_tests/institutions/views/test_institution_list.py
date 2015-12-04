from nose.tools import *

from tests.base import ApiTestCase
from tests.factories import InstitutionFactory

from api.base.settings.defaults import API_BASE

class TestInstitutionList(ApiTestCase):
    def setUp(self):
        super(TestInstitutionList, self).setUp()
        self.institution = InstitutionFactory()
        self.institution2 = InstitutionFactory()
        self.institution_url = '/{}institutions/'.format(API_BASE)

    def test_return_all_institutions(self):
        res = self.app.get(self.institution_url)

        assert_equal(res.status_code, 200)
        assert_equal(len(res.json['data']), 2)

from nose.tools import *  # flake8: noqa

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

        ids = [each['id'] for each in res.json['data']]
        assert_equal(len(res.json['data']), 2)
        assert_in(self.institution._id, ids)
        assert_in(self.institution2._id, ids)

from nose.tools import *  # flake8: noqa

from tests.base import ApiTestCase
from tests.factories import InstitutionFactory

from api.base.settings.defaults import API_BASE

class TestInstitutionDetail(ApiTestCase):
    def setUp(self):
        super(TestInstitutionDetail, self).setUp()
        self.institution = InstitutionFactory()
        self.institution_url = '/' + API_BASE + 'institutions/{id}/'

    def test_return_wrong_id(self):
        res = self.app.get(self.institution_url.format(id='1PO'), expect_errors=True)

        assert_equal(res.status_code, 404)

    def test_return_with_id(self):
        res = self.app.get(self.institution_url.format(id=self.institution._id))

        assert_equal(res.status_code, 200)
        assert_equal(res.json['data']['attributes']['name'], self.institution.name)

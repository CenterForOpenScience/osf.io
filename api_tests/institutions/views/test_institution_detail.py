import pytest

from api.base.settings.defaults import API_BASE
from osf_tests.factories import InstitutionFactory

@pytest.mark.django_db
class TestInstitutionDetail:

    @pytest.fixture()
    def institution(self):
        return InstitutionFactory()

    @pytest.fixture()
    def url_institution(self):
        def url(id):
            return '/{}institutions/{}/'.format(API_BASE, id)
        return url


    def test_detail_response(self, app, institution, url_institution):
        #return_wrong_id
        res = app.get(url_institution(id='1PO'), expect_errors=True)
        assert res.status_code == 404

        #test_return_with_id
        res = app.get(url_institution(id=institution._id))

        assert res.status_code == 200
        assert res.json['data']['attributes']['name'] == institution.name

import pytest

from api.base.settings.defaults import API_BASE
from osf_tests.factories import InstitutionFactory


@pytest.mark.django_db
class TestInstitutionDetail:

    def test_detail_response(self, app):
        institution = InstitutionFactory()

        # return_wrong_id
        url = '/{}institutions/{}/'.format(API_BASE, '1PO')
        res = app.get(url, expect_errors=True)
        assert res.status_code == 404

        # test_return_with_id
        url = '/{}institutions/{}/'.format(API_BASE, institution._id)
        res = app.get(url)
        assert res.status_code == 200
        assert res.json['data']['attributes']['name'] == institution.name
        assert 'logo_path' in res.json['data']['attributes']
        assert 'assets' in res.json['data']['attributes']
        assert 'logo' in res.json['data']['attributes']['assets']
        assert 'logo_rounded' in res.json['data']['attributes']['assets']

        # test_return_without_logo_path
        url = '/{}institutions/{}/?version=2.14&'.format(API_BASE, institution._id)
        res = app.get(url)
        assert res.status_code == 200
        assert 'logo_path' not in res.json['data']['attributes']

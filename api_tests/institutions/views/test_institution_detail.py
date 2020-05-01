import pytest

from osf_tests.factories import InstitutionFactory
from api.base.settings.defaults import API_BASE
from django.core.validators import URLValidator

@pytest.mark.django_db
class TestInstitutionDetail:

    expected_relationships = {
        'nodes',
        'registrations',
        'users',
        'department_metrics',
        'user_metrics',
        'summary_metrics'
    }

    is_valid_url = URLValidator()

    @pytest.fixture()
    def institution(self):
        return InstitutionFactory()

    @pytest.fixture()
    def url(self, institution):
        return f'/{API_BASE}institutions/{institution._id}/'

    def test_detail_response(self, app, institution, url):

        # 404 on wrong _id
        res = app.get(f'/{institution}institutions/1PO/', expect_errors=True)
        assert res.status_code == 404

        res = app.get(url)
        assert res.status_code == 200
        assert res.json['data']['attributes']['name'] == institution.name
        assert 'logo_path' in res.json['data']['attributes']
        assert 'assets' in res.json['data']['attributes']
        assert 'logo' in res.json['data']['attributes']['assets']
        assert 'logo_rounded' in res.json['data']['attributes']['assets']

        relationships = res.json['data']['relationships']
        assert self.expected_relationships == set(relationships.keys())
        for relationships in list(relationships.values()):
            # ↓ returns None if url is valid else throws error.
            assert self.is_valid_url(relationships['links']['related']['href']) is None

        # test_return_without_logo_path
        res = app.get(f'{url}?version=2.14')
        assert res.status_code == 200
        assert 'logo_path' not in res.json['data']['attributes']

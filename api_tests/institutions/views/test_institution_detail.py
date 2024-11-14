import pytest

from osf_tests.factories import (
    AuthUserFactory,
    InstitutionFactory,
)
from api.base.settings.defaults import API_BASE
from django.core.validators import URLValidator

@pytest.mark.django_db
class TestInstitutionDetail:

    expected_relationships = {
        'nodes',
        'registrations',
        'users',
    }
    expected_metrics_relationships = {
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

    @pytest.fixture()
    def rando(self):
        return AuthUserFactory()

    @pytest.fixture()
    def institutional_admin(self, institution):
        _admin_user = AuthUserFactory()
        institution.get_group('institutional_admins').user_set.add(_admin_user)
        return _admin_user

    def test_detail_response(self, app, institution, url, rando, institutional_admin):

        for _user in (None, rando, institutional_admin):
            _auth = (None if _user is None else _user.auth)
            # 404 on wrong _id
            res = app.get(f'/{institution}institutions/1PO/', expect_errors=True, auth=_auth)
            assert res.status_code == 404

            res = app.get(url, auth=_auth)
            assert res.status_code == 200
            attrs = res.json['data']['attributes']
            assert attrs['name'] == institution.name
            assert attrs['iri'] == institution.identifier_domain
            assert attrs['ror_iri'] == institution.ror_uri
            assert set(attrs['iris']) == {
                institution.ror_uri,
                institution.identifier_domain,
                institution.absolute_url,
            }
            assert 'logo_path' in attrs
            assert set(attrs['assets'].keys()) == {'logo', 'logo_rounded', 'banner'}
            if _user is institutional_admin:
                assert attrs['link_to_external_reports_archive'] == institution.link_to_external_reports_archive
            else:
                assert 'link_to_external_reports_archive' not in attrs
            assert res.json['data']['links']['self'].endswith(url)

            relationships = res.json['data']['relationships']
            _expected_relationships = (
                self.expected_relationships | self.expected_metrics_relationships
                if _user is institutional_admin
                else self.expected_relationships
            )
            assert _expected_relationships == set(relationships.keys())
            for relationships in list(relationships.values()):
                # ↓ returns None if url is valid else throws error.
                assert self.is_valid_url(relationships['links']['related']['href']) is None

            # test_return_without_logo_path
            res = app.get(f'{url}?version=2.14', auth=_auth)
            assert res.status_code == 200
            assert 'logo_path' not in res.json['data']['attributes']

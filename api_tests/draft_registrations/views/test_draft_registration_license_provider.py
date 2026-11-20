import pytest

from api.base.settings.defaults import API_BASE
from osf.models import NodeLicense
from osf_tests.factories import (
    AuthUserFactory,
    DraftRegistrationFactory,
    RegistrationProviderFactory,
)


@pytest.mark.django_db
class TestDraftRegistrationLicenseEnforcedByProvider:

    @pytest.fixture()
    def user(self):
        return AuthUserFactory()

    @pytest.fixture()
    def cc0(self):
        return NodeLicense.objects.get(name='CC0 1.0 Universal')

    @pytest.fixture()
    def mit(self):
        return NodeLicense.objects.get(name='MIT License')

    @pytest.fixture()
    def provider(self, cc0):
        provider = RegistrationProviderFactory()
        provider.licenses_acceptable.add(cc0)
        return provider

    @pytest.fixture()
    def draft(self, user, provider):
        return DraftRegistrationFactory(initiator=user, provider=provider)

    def payload(self, draft, license_id):
        return {
            'data': {
                'type': 'draft_registrations',
                'id': draft._id,
                'attributes': {'node_license': {'year': '2026', 'copyright_holders': ['A']}},
                'relationships': {'license': {'data': {'type': 'licenses', 'id': license_id}}},
            },
        }

    def test_accepted_license(self, app, user, draft, cc0):
        res = app.patch_json_api(
            f'/{API_BASE}draft_registrations/{draft._id}/', self.payload(draft, cc0._id), auth=user.auth,
        )
        assert res.status_code == 200

    def test_unaccepted_license(self, app, user, draft, provider, mit):
        res = app.patch_json_api(
            f'/{API_BASE}draft_registrations/{draft._id}/', self.payload(draft, mit._id),
            auth=user.auth, expect_errors=True,
        )
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == f"The license '{mit.name}' is not accepted by {provider.name}."

    def test_no_license_always_rejected(self, app, user, draft, provider):
        no_license = NodeLicense.objects.get(license_id='NONE')
        provider.licenses_acceptable.add(no_license)
        res = app.patch_json_api(
            f'/{API_BASE}draft_registrations/{draft._id}/', self.payload(draft, no_license._id),
            auth=user.auth, expect_errors=True,
        )
        assert res.status_code == 400
        assert 'Registrations require a license' in res.json['errors'][0]['detail']

    def test_null_node_license_has_clear_message(self, app, user, draft):
        res = app.patch_json_api(
            f'/{API_BASE}draft_registrations/{draft._id}/',
            {'data': {'type': 'draft_registrations', 'id': draft._id, 'attributes': {'node_license': None}}},
            auth=user.auth, expect_errors=True,
        )
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'A license is required for a registration.'

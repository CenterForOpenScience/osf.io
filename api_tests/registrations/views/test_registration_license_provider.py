import pytest

from api.base.settings.defaults import API_BASE
from osf.models import NodeLicense
from osf_tests.factories import (
    AuthUserFactory,
    EmbargoFactory,
    RegistrationFactory,
    RegistrationProviderFactory,
    ProjectFactory,
    NodeLicenseRecordFactory,
)


def license_payload(registration_id, license_id, year='2026', holders=None):
    return {
        'data': {
            'type': 'registrations',
            'id': registration_id,
            'attributes': {
                'node_license': {
                    'year': year,
                    'copyright_holders': holders or ['Someone'],
                },
            },
            'relationships': {
                'license': {'data': {'type': 'licenses', 'id': license_id}},
            },
        },
    }


@pytest.mark.django_db
class TestRegistrationLicenseEnforcedByProvider:

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
    def no_license(self):
        return NodeLicense.objects.get(license_id='NONE')

    @pytest.fixture()
    def provider(self, cc0):
        provider = RegistrationProviderFactory()
        provider.licenses_acceptable.add(cc0)
        return provider

    @pytest.fixture()
    def registration(self, user, provider, cc0):
        reg = RegistrationFactory(creator=user, provider=provider, is_public=True)
        reg.node_license = NodeLicenseRecordFactory(node_license=cc0)
        reg.save()
        return reg

    def url(self, registration):
        return f'/{API_BASE}registrations/{registration._id}/'

    def test_accepted_license_saves(self, app, user, registration, cc0):
        res = app.patch_json_api(
            self.url(registration),
            license_payload(registration._id, cc0._id, year='2030'),
            auth=user.auth,
        )
        assert res.status_code == 200
        assert res.json['data']['attributes']['node_license']['year'] == '2030'

    def test_unaccepted_license_rejected(self, app, user, registration, provider, mit):
        res = app.patch_json_api(
            self.url(registration),
            license_payload(registration._id, mit._id),
            auth=user.auth,
            expect_errors=True,
        )
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == f"The license '{mit.name}' is not accepted by {provider.name}."
        registration.refresh_from_db()
        assert registration.node_license.node_license != mit

    def test_no_license_always_rejected_for_registrations(self, app, user, registration, provider, no_license):
        # rejected when the provider does not list it...
        res = app.patch_json_api(
            self.url(registration),
            license_payload(registration._id, no_license._id),
            auth=user.auth,
            expect_errors=True,
        )
        assert res.status_code == 400
        assert 'is not accepted by' in res.json['errors'][0]['detail']
        assert 'Registrations require a license' in res.json['errors'][0]['detail']

        # ...and also when it does
        provider.licenses_acceptable.add(no_license)
        res = app.patch_json_api(
            self.url(registration),
            license_payload(registration._id, no_license._id),
            auth=user.auth,
            expect_errors=True,
        )
        assert res.status_code == 400
        assert 'Registrations require a license' in res.json['errors'][0]['detail']
        registration.refresh_from_db()
        assert registration.node_license.node_license != no_license

    def test_null_node_license_has_clear_message(self, app, user, registration):
        res = app.patch_json_api(
            self.url(registration),
            {'data': {'type': 'registrations', 'id': registration._id, 'attributes': {'node_license': None}}},
            auth=user.auth,
            expect_errors=True,
        )
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'A license is required for a registration.'

    def test_null_license_relationship_rejected(self, app, user, registration):
        res = app.patch_json_api(
            self.url(registration),
            {'data': {'type': 'registrations', 'id': registration._id, 'relationships': {'license': {'data': None}}}},
            auth=user.auth,
            expect_errors=True,
        )
        assert res.status_code == 400
        registration.refresh_from_db()
        assert registration.node_license is not None

    def test_provider_without_restrictions_accepts_any_license(self, app, user, registration, provider, mit):
        provider.licenses_acceptable.clear()
        res = app.patch_json_api(
            self.url(registration),
            license_payload(registration._id, mit._id),
            auth=user.auth,
        )
        assert res.status_code == 200

    def test_embargoed_registration_enforced(self, app, user, provider, cc0, mit):
        reg = RegistrationFactory(creator=user, provider=provider, embargo=EmbargoFactory(user=user), is_public=False)
        reg.node_license = NodeLicenseRecordFactory(node_license=cc0)
        reg.save()
        res = app.patch_json_api(
            self.url(reg),
            license_payload(reg._id, mit._id),
            auth=user.auth,
            expect_errors=True,
        )
        assert res.status_code == 400

        res = app.patch_json_api(
            self.url(reg),
            license_payload(reg._id, cc0._id),
            auth=user.auth,
        )
        assert res.status_code == 200

    def test_registering_still_works_with_unaccepted_license(self, user, provider, mit):
        project = ProjectFactory(creator=user)
        project.node_license = NodeLicenseRecordFactory(node_license=mit)
        project.save()
        reg = RegistrationFactory(project=project, creator=user, provider=provider)
        assert reg.node_license.node_license == mit

import pytest

from framework.auth import Auth
from osf.exceptions import LicenseNotAcceptedError
from osf.models import NodeLicense
from osf_tests.factories import (
    AuthUserFactory,
    DraftRegistrationFactory,
    RegistrationProviderFactory,
)
from website.project.licenses import validate_license_for_provider


@pytest.mark.django_db
class TestValidateLicenseForProvider:

    @pytest.fixture()
    def cc0(self):
        return NodeLicense.objects.get(name='CC0 1.0 Universal')

    @pytest.fixture()
    def mit(self):
        return NodeLicense.objects.get(name='MIT License')

    def test_empty_list_accepts_anything(self, mit):
        validate_license_for_provider(RegistrationProviderFactory(), mit)

    def test_accepted(self, cc0):
        provider = RegistrationProviderFactory()
        provider.licenses_acceptable.add(cc0)
        validate_license_for_provider(provider, cc0)

    def test_not_accepted(self, cc0, mit):
        provider = RegistrationProviderFactory()
        provider.licenses_acceptable.add(cc0)
        with pytest.raises(LicenseNotAcceptedError, match='is not accepted by'):
            validate_license_for_provider(provider, mit)

    def test_draft_registration_enforced(self, cc0, mit):
        user = AuthUserFactory()
        provider = RegistrationProviderFactory()
        provider.licenses_acceptable.add(cc0)
        draft = DraftRegistrationFactory(initiator=user, provider=provider)
        auth = Auth(user)
        draft.set_node_license({'id': cc0.license_id, 'year': '2026', 'copyrightHolders': ['A']}, auth)
        with pytest.raises(LicenseNotAcceptedError):
            draft.set_node_license({'id': mit.license_id, 'year': '2026', 'copyrightHolders': ['A']}, auth)

    def test_no_license_rejected_for_registration_even_if_provider_lists_it(self, cc0):
        user = AuthUserFactory()
        no_license = NodeLicense.objects.get(license_id='NONE')
        provider = RegistrationProviderFactory()
        provider.licenses_acceptable.add(cc0, no_license)
        draft = DraftRegistrationFactory(initiator=user, provider=provider)
        with pytest.raises(LicenseNotAcceptedError, match='Registrations require a license'):
            draft.set_node_license({'id': 'NONE', 'year': '2026', 'copyrightHolders': ['A']}, Auth(user))

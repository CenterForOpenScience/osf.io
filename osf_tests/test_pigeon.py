import mock
import json
import pytest
from website import settings
from osf_tests.factories import RegistrationFactory, AuthUserFactory, EmbargoFactory, RegistrationApprovalFactory

@pytest.mark.django_db
class TestPigeon:

    @pytest.fixture()
    def user(self):
        return AuthUserFactory()

    @pytest.fixture()
    def registration(self):
        return RegistrationFactory()

    @pytest.fixture()
    def embargo(self):
        return EmbargoFactory()

    @pytest.fixture()
    def registration_approval(self, user):
        return RegistrationApprovalFactory(state='unapproved', user=user)

    def test_pigeon_sync_metadata(self, mock_pigeon, registration):
        registration.is_public = True
        registration.ia_url = 'http://archive.org/details/osf-registrations-guid0-v1'
        registration.title = 'Jefferies'
        registration.save()

        assert len(mock_pigeon.calls) == 1

        data = json.loads(mock_pigeon.calls[0].request.body.decode())
        assert data == {
            'modified': mock.ANY,
            'title': 'Jefferies',
        }

        registration.title = 'Private'
        registration.is_public = False
        registration.save()

        assert len(mock_pigeon.calls) == 1

    def test_pigeon_archive_immediately(self, user, registration_approval, mock_datacite, mock_pigeon):
        mock_pigeon._matches += mock_datacite._matches  # mock both of these together
        token = registration_approval.approval_state[registration_approval.initiated_by._id]['approval_token']
        registration_approval.approve(user=registration_approval.initiated_by, token=token)
        guid = registration_approval._get_registration()._id

        assert len(mock_pigeon.calls) == 3
        calls = [call.request.url for call in mock_pigeon.calls]
        assert calls == [f'{settings.DATACITE_URL}/metadata',
                        f'{settings.DATACITE_URL}/doi',
                        f'{settings.OSF_PIGEON_URL}archive/{guid}']

    def test_pigeon_archive_embargo(self, embargo, mock_pigeon):
        token = embargo.approval_state[embargo.initiated_by._id]['approval_token']
        embargo.approve(user=embargo.initiated_by, token=token)
        guid = embargo._get_registration()._id

        assert len(mock_pigeon.calls) == 1
        assert mock_pigeon.calls[0].request.url == f'{settings.OSF_PIGEON_URL}archive/{guid}'

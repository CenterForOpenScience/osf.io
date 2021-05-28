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
        embargo = EmbargoFactory()
        embargo.accept()
        return embargo

    @pytest.fixture()
    def registration_approval(self, user):
        return RegistrationApprovalFactory(state='unapproved', user=user)

    @pytest.mark.enable_enqueue_task
    @pytest.mark.enable_implicit_clean
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

    @pytest.mark.enable_enqueue_task
    @pytest.mark.enable_implicit_clean
    def test_pigeon_archive_immediately(self, registration, mock_pigeon):
        registration.is_public = True
        registration.save()

        calls = [call.request.url for call in mock_pigeon.calls]
        assert len(mock_pigeon.calls) == 2
        assert calls == [
            f'{settings.OSF_PIGEON_URL}metadata/{registration._id}',
            f'{settings.OSF_PIGEON_URL}archive/{registration._id}',
        ]

    @pytest.mark.enable_enqueue_task
    @pytest.mark.enable_implicit_clean
    def test_pigeon_archive_embargo(self, embargo, mock_pigeon):
        embargo._get_registration().terminate_embargo()
        guid = embargo._get_registration()._id

        calls = [call.request.url for call in mock_pigeon.calls]
        assert len(mock_pigeon.calls) == 2
        assert calls == [
            f'{settings.OSF_PIGEON_URL}metadata/{guid}',
            f'{settings.OSF_PIGEON_URL}archive/{guid}',
        ]

import re
import mock
import pytest
import responses
from urllib.parse import unquote, parse_qs
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

    def test_pigeon_sync_metadata(self, mock_ia, registration):
        registration.is_public = True
        registration.save()

        GET_metadata, POST_metadata, GET_metadata_again = mock_ia.calls

        ia_id = f'osf-registrations-{registration._id}-{registration.registered_date.strftime("%Y-%m-%dT%H-%M-%S.%f")}-{settings.IA_ID_VERSION}'
        assert GET_metadata.request.url == f'https://archive.org/metadata/{ia_id}'
        assert GET_metadata.request.method == 'GET'
        assert GET_metadata.request.body is None

        assert POST_metadata.request.url == f'https://archive.org/metadata/{ia_id}'
        assert POST_metadata.request.method == 'POST'
        parse_qs(unquote(POST_metadata.request.body))['-patch'] == [{
            'op': 'add',
            'path': '/modified',
            'value': mock.ANY
        }, {
            'op': 'add',
            'path': '/is_public',
            'value': True
        }]

        assert GET_metadata_again.request.url == f'https://archive.org/metadata/{ia_id}'
        assert GET_metadata_again.request.method == 'GET'
        assert GET_metadata_again.request.body is None

    def test_pigeon_sync_metadata_fails(self, mock_sentry, mock_ia, registration):
        mock_ia.reset()  # removed mocked urls to simulate IA being down
        mock_ia.add(
            responses.GET,
            re.compile('https://archive.org/metadata/(.*)'),
            status=500
        )
        registration.is_public = True
        registration.save()
        assert len(mock_ia.calls) == 1
        mock_sentry.assert_called_with(extra={'session': {}})

    def test_pigeon_archive_immediately(self, user, mock_pigeon, mock_ia, registration_approval):
        token = registration_approval.approval_state[registration_approval.initiated_by._id]['approval_token']
        registration_approval.approve(user=registration_approval.initiated_by, token=token)
        mock_ia.add(responses.POST, 'https://mds.test.datacite.org/metadata', status=200)

        mock_ia.add(
            responses.GET,
            re.compile('https://archive.org/metadata/(.*)'),
            status=500
        )

        mock_pigeon.assert_called_with(
            registration_approval._get_registration()._id,
            datacite_password='test_datacite_password',
            datacite_username='test_datacite_username',
            ia_access_key='test_ia_access_key',
            ia_secret_key='test_ia_secret_key',
            osf_files_url=settings.WATERBUTLER_URL + '/',
            osf_api_url=settings.API_DOMAIN,
            collection_name=settings.IA_ROOT_COLLECTION,
            id_version=settings.IA_ID_VERSION
        )

    def test_pigeon_archive_embargo(self, mock_sentry, mock_pigeon, embargo):
        token = embargo.approval_state[embargo.initiated_by._id]['approval_token']
        embargo.approve(user=embargo.initiated_by, token=token)

        mock_pigeon.assert_called_with(
            embargo._get_registration()._id,
            datacite_password='test_datacite_password',
            datacite_username='test_datacite_username',
            ia_access_key='test_ia_access_key',
            ia_secret_key='test_ia_secret_key',
            osf_files_url=settings.WATERBUTLER_URL + '/',
            osf_api_url=settings.API_DOMAIN,
            collection_name=settings.IA_ROOT_COLLECTION,
            id_version=settings.IA_ID_VERSION
        )

        embargo._get_registration().refresh_from_db()
        assert embargo._get_registration().IA_url == 'http://briandawkinsongameday.com'

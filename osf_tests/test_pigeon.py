import re
import mock
import pytest
import responses
from urllib.parse import unquote, parse_qs

from osf_tests.factories import RegistrationFactory, AuthUserFactory

@pytest.mark.django_db
class TestPigeon:

    @pytest.fixture()
    def user(self):
        return AuthUserFactory()

    @pytest.fixture()
    def registration(self):
        return RegistrationFactory()

    def test_pigeon_sync_metadata(self, mock_pigeon, registration):
        registration.is_public = True
        registration.save()

        GET_metadata, POST_metadata, GET_metadata_again = mock_pigeon.calls

        assert GET_metadata.request.url == f'https://archive.org/metadata/{registration._id}'
        assert GET_metadata.request.method == 'GET'
        assert GET_metadata.request.body is None

        assert POST_metadata.request.url == f'https://archive.org/metadata/{registration._id}'
        assert POST_metadata.request.method == 'POST'
        parse_qs(unquote(mock_pigeon.calls[1].request.body))['-patch'] == [{
            'op': 'add',
            'path': '/modified',
            'value': mock.ANY
        }, {
            'op': 'add',
            'path': '/is_public',
            'value': True
        }]

        assert GET_metadata_again.request.url == f'https://archive.org/metadata/{registration._id}'
        assert GET_metadata_again.request.method == 'GET'
        assert GET_metadata_again.request.body is None

    def test_pigeon_sync_metadata_fails(self, mock_sentry, mock_pigeon, registration):
        mock_pigeon.reset()  # removed mocked urls to simulate a timeout
        mock_pigeon.add(
            responses.GET,
            re.compile('https://archive.org/metadata/(.*)'),
            body=b'{}',
            status=200
        )
        registration.is_public = True
        registration.save()
        mock_sentry.assert_called_with(extra={'session': {}})
        assert len(mock_pigeon.calls) == 4  # one real request and three failed retries

        mock_pigeon.reset()  # removed mocked urls to simulate IA being down
        mock_pigeon.add(
            responses.GET,
            re.compile('https://archive.org/metadata/(.*)'),
            status=500
        )
        registration.is_public = True
        registration.save()
        assert len(mock_pigeon.calls) == 1
        mock_sentry.assert_called_with(extra={'session': {}})

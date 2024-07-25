import pytest
from unittest import mock
import hashlib
from rest_framework.exceptions import NotFound

from osf.registrations.utils import DuplicateHeadersError, FileUploadNotSupportedError, InvalidHeadersError
from api.base.settings import BULK_SETTINGS
from osf_tests.factories import (
    AuthUserFactory,
    RegistrationProviderFactory,
    RegistrationBulkUploadJobFactory,
)
from webtest_plus.app import _add_auth

@pytest.mark.django_db
class TestRegistrationBulkUpload():

    @pytest.fixture()
    def unauthorized_user(self):
        return AuthUserFactory()

    @pytest.fixture()
    def user(self):
        return AuthUserFactory()

    @pytest.fixture()
    def provider_allow_bulk(self, user):
        provider = RegistrationProviderFactory()
        provider.allow_bulk_uploads = True
        provider.add_to_group(user, 'admin')
        provider.save()
        return provider

    @pytest.fixture()
    def provider_not_allow_bulk(self, user):
        provider = RegistrationProviderFactory()
        provider.allow_bulk_uploads = False
        provider.add_to_group(user, 'admin')
        provider.save()
        return provider

    @pytest.fixture()
    def url_allow_bulk_upload(self, provider_allow_bulk):
        return f'/_/registries/{provider_allow_bulk._id}/bulk_create/file.csv/'

    @pytest.fixture()
    def url_not_allow_bulk_upload(self, provider_not_allow_bulk):
        return f'/_/registries/{provider_not_allow_bulk._id}/bulk_create/file.csv/'

    @pytest.fixture()
    def file_content_exceeds_limit(self):
        return ('a' * BULK_SETTINGS['DEFAULT_BULK_LIMIT'] * 10001).encode()

    @pytest.fixture()
    def file_content_legit(self):
        return ('a' * BULK_SETTINGS['DEFAULT_BULK_LIMIT'] * 1).encode()

    def test_unauthorized_user(self, app, unauthorized_user, url_not_allow_bulk_upload, url_allow_bulk_upload):
        resp = app.put(url_allow_bulk_upload, auth=unauthorized_user.auth, expect_errors=True)
        assert resp.status_code == 403
        resp = app.put(url_not_allow_bulk_upload, auth=unauthorized_user.auth, expect_errors=True)
        assert resp.status_code == 403

    def test_bulk_upload_not_allowed(self, app, user, url_not_allow_bulk_upload):
        resp = app.put(url_not_allow_bulk_upload, auth=user.auth, expect_errors=True)
        assert len(resp.json['errors']) == 1
        assert resp.json['errors'][0]['type'] == 'bulkUploadNotAllowed'

    def test_exceeds_size_limit(self, app, user, url_allow_bulk_upload, file_content_exceeds_limit):
        resp = app.request(
            url_allow_bulk_upload,
            method='PUT',
            expect_errors=True,
            body=file_content_exceeds_limit,
            headers=_add_auth(user.auth, None),
            content_type='text/csv',
        )
        assert len(resp.json['errors']) == 1
        assert resp.json['errors'][0]['type'] == 'sizeExceedsLimit'
        assert resp.status_code == 413

    def test_wrong_content_type(self, app, user, url_allow_bulk_upload, file_content_legit):
        resp = app.request(
            url_allow_bulk_upload,
            method='PUT',
            expect_errors=True,
            body=file_content_legit,
            headers=_add_auth(user.auth, None),
            content_type='text/plain',
        )
        assert len(resp.json['errors']) == 1
        assert resp.json['errors'][0]['type'] == 'invalidFileType'
        assert resp.status_code == 413

    def test_bulk_upload_job_exists(self, app, user, url_allow_bulk_upload, file_content_legit):
        file_hash = hashlib.md5()
        file_hash.update(file_content_legit)
        RegistrationBulkUploadJobFactory(payload_hash=file_hash.hexdigest())
        resp = app.request(
            url_allow_bulk_upload,
            method='PUT',
            expect_errors=True,
            body=file_content_legit,
            headers=_add_auth(user.auth, None),
            content_type='text/csv',
        )
        assert len(resp.json['errors']) == 1
        assert resp.json['errors'][0]['type'] == 'bulkUploadJobExists'
        assert resp.status_code == 409

    @mock.patch('api.providers.views.BulkRegistrationUpload.__init__')
    @mock.patch('api.providers.views.BulkRegistrationUpload.validate')
    def test_invalid_headers(self, mock___init__, mock_validate, app, user, url_allow_bulk_upload, file_content_legit):
        mock___init__.return_value = None
        mock_validate.side_effect = InvalidHeadersError({'invalid_headers': ['a'], 'missing_headers': ['b']})
        resp = app.request(
            url_allow_bulk_upload,
            method='PUT',
            expect_errors=True,
            body=file_content_legit,
            headers=_add_auth(user.auth, None),
            content_type='text/csv',
        )
        assert len(resp.json['errors']) == 1
        assert resp.json['errors'][0]['type'] == 'invalidColumnId'
        assert resp.json['errors'][0]['invalidHeaders'] == ['a']
        assert resp.json['errors'][0]['missingHeaders'] == ['b']
        assert resp.status_code == 400

    @mock.patch('api.providers.views.BulkRegistrationUpload.__init__')
    @mock.patch('api.providers.views.BulkRegistrationUpload.validate')
    def test_duplicate_headers(self, mock___init__, mock_validate, app, user, url_allow_bulk_upload, file_content_legit):
        mock___init__.return_value = None
        mock_validate.side_effect = DuplicateHeadersError({'duplicate_headers': ['a']})
        resp = app.request(
            url_allow_bulk_upload,
            method='PUT',
            expect_errors=True,
            body=file_content_legit,
            headers=_add_auth(user.auth, None),
            content_type='text/csv',
        )
        assert len(resp.json['errors']) == 1
        assert resp.json['errors'][0]['type'] == 'duplicateColumnId'
        assert resp.json['errors'][0]['duplicateHeaders'] == ['a']
        assert resp.status_code == 400

    @mock.patch('api.providers.views.BulkRegistrationUpload.__init__')
    @mock.patch('api.providers.views.BulkRegistrationUpload.validate')
    def test_file_upload_not_supported(self, mock___init__, mock_validate, app, user, url_allow_bulk_upload, file_content_legit):
        mock___init__.return_value = None
        mock_validate.side_effect = FileUploadNotSupportedError()
        resp = app.request(
            url_allow_bulk_upload,
            method='PUT',
            expect_errors=True,
            body=file_content_legit,
            headers=_add_auth(user.auth, None),
            content_type='text/csv',
        )
        assert len(resp.json['errors']) == 1
        assert resp.json['errors'][0]['type'] == 'fileUploadNotSupported'
        assert resp.status_code == 400

    @mock.patch('api.providers.views.BulkRegistrationUpload.__init__')
    @mock.patch('api.providers.views.BulkRegistrationUpload.validate')
    def test_schema_not_found(self, mock___init__, mock_validate, app, user, url_allow_bulk_upload, file_content_legit):
        mock___init__.return_value = None
        mock_validate.side_effect = NotFound
        resp = app.request(
            url_allow_bulk_upload,
            method='PUT',
            expect_errors=True,
            body=file_content_legit,
            headers=_add_auth(user.auth, None),
            content_type='text/csv',
        )
        assert len(resp.json['errors']) == 1
        assert resp.json['errors'][0]['type'] == 'invalidSchemaId'
        assert resp.status_code == 404

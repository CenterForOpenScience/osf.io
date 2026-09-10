from unittest import mock

from django.test import override_settings
from django.utils import timezone

from admin.files.tasks import purge_file_version_task
from api_tests.utils import create_test_file
from osf.models.files import BaseFileVersionsThrough
from tests.base import AdminTestCase
from osf_tests.factories import AuthUserFactory, ProjectFactory


class TestPurgeFileVersionTask(AdminTestCase):
    def setUp(self):
        super().setUp()
        self.node = ProjectFactory()
        self.user = AuthUserFactory()
        self.test_file = create_test_file(self.node, self.user)
        self.version = self.test_file.versions.first()
        BaseFileVersionsThrough.objects.filter(
            basefilenode=self.test_file, fileversion=self.version
        ).delete()

    @override_settings(GCS_CREDS=None)
    def test_no_gcs_creds_configured_is_noop(self):
        with mock.patch.object(type(self.version), '_purge') as mock_purge:
            result = purge_file_version_task(self.version.pk)
        mock_purge.assert_not_called()
        assert result == 0

    @override_settings(GCS_CREDS='/fake/path/to/creds.json')
    def test_purges_with_gcs_client(self):
        fake_client = mock.Mock()
        with mock.patch('google.oauth2.service_account.Credentials.from_service_account_file') as mock_creds, \
             mock.patch('google.cloud.storage.client.Client', return_value=fake_client), \
             mock.patch.object(type(self.version), '_purge', return_value=1337) as mock_purge:
            result = purge_file_version_task(self.version.pk)

        mock_creds.assert_called_once_with('/fake/path/to/creds.json')
        mock_purge.assert_called_once_with(client=fake_client)
        assert result == 1337

    @override_settings(GCS_CREDS='/fake/path/to/creds.json')
    def test_already_purged_version_is_noop(self):
        self.version.purged = timezone.now()
        self.version.save()

        with mock.patch.object(type(self.version), '_purge') as mock_purge:
            result = purge_file_version_task(self.version.pk)
        mock_purge.assert_not_called()
        assert result == 0

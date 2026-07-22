import time

import pytest

from addons.osfstorage.settings import DEFAULT_REGION_NAME
from api_tests.utils import create_test_file
from framework.auth import signing
from osf.models import DownloadEvent
from osf.utils.download_telemetry import derive_user_region, record_download
from osf_tests.factories import AuthUserFactory, ProjectFactory
from tests.base import OsfTestCase


class TestZipDownloadTelemetry(OsfTestCase):
    """Folder and project zips, recorded from the WaterButler callback.

    Zips are requested straight from WaterButler, so this callback is the only place we
    hear about them.
    """

    def setUp(self):
        super().setUp()
        self.user = AuthUserFactory()
        self.node = ProjectFactory(creator=self.user)
        self.url = self.node.api_url_for('create_waterbutler_log')

    def build_payload(self, materialized='/', action='download_zip', **action_meta):
        meta = dict(
            bytes_downloaded=2048,
            completed=True,
            ip='198.51.100.7',
            source='files',
            tz='Europe/Kyiv',
        )
        meta.update(action_meta)
        options = {
            'auth': {'id': self.user._id},
            'action': action,
            'provider': 'osfstorage',
            'time': time.time() + 1000,
            'metadata': {
                'nid': self.node._id,
                'materialized': materialized,
                'path': materialized,
                'kind': 'folder',
                'provider': 'osfstorage',
            },
            'action_meta': meta,
        }
        message, signature = signing.default_signer.sign_payload(options)
        return {'payload': message, 'signature': signature}

    def test_project_zip_is_recorded(self):
        res = self.app.put(self.url, json=self.build_payload(materialized='/'))

        assert res.status_code == 200
        event = DownloadEvent.objects.get()
        assert event.download_type == DownloadEvent.PROJECT
        assert event.resource_guid == self.node._id
        assert event.user == self.user
        assert event.size_bytes == 2048
        assert event.zip_completed is True
        assert event.ip == '198.51.100.7'
        assert event.source_area == 'files'
        assert event.user_region == 'Europe/Kyiv'

    def test_folder_zip_is_recorded_with_its_path(self):
        self.app.put(self.url, json=self.build_payload(materialized='/data/raw/'))

        event = DownloadEvent.objects.get()
        assert event.download_type == DownloadEvent.FOLDER_ZIP
        assert event.path == '/data/raw/'

    def test_incomplete_zip_is_recorded_as_incomplete(self):
        self.app.put(self.url, json=self.build_payload(completed=False))

        assert DownloadEvent.objects.get().zip_completed is False

    def test_mfr_render_is_not_recorded(self):
        self.app.put(self.url, json=self.build_payload(is_mfr_render=True))

        assert not DownloadEvent.objects.exists()

    def test_single_file_action_is_not_recorded_here(self):
        """Single files are caught at the redirect view — recording them here too would
        double count every one of them."""
        self.app.put(self.url, json=self.build_payload(action='download_file'))

        assert not DownloadEvent.objects.exists()

    def test_oversized_source_is_truncated_to_the_column(self):
        self.app.put(self.url, json=self.build_payload(source='f' * 500))

        assert len(DownloadEvent.objects.get().source_area) == 128

    def test_callback_still_succeeds_when_recording_fails(self, ):
        with pytest.MonkeyPatch.context() as patch:
            patch.setattr(
                'addons.base.views.record_download',
                lambda **kwargs: (_ for _ in ()).throw(ValueError('boom')),
            )
            res = self.app.put(self.url, json=self.build_payload())

        assert res.status_code == 200


class TestSingleFileDownloadTelemetry(OsfTestCase):
    """Single files, recorded at the redirect view before we 302 on to WaterButler."""

    def setUp(self):
        super().setUp()
        self.user = AuthUserFactory()
        self.node = ProjectFactory(creator=self.user)
        self.file = create_test_file(self.node, self.user, size=4096)
        self.guid = self.file.get_guid()._id

    def test_download_is_recorded_with_link_tags(self):
        res = self.app.get(
            f'/download/{self.guid}/?source=file-detail&tz=Europe%2FKyiv',
            auth=self.user.auth,
        )

        assert res.status_code == 302
        event = DownloadEvent.objects.get()
        assert event.download_type == DownloadEvent.FILE
        assert event.resource_guid == self.node._id
        assert event.user == self.user
        assert event.source_area == 'file-detail'
        assert event.user_region == 'Europe/Kyiv'

    def test_size_and_region_come_from_the_file_version(self):
        self.app.get(f'/download/{self.guid}/', auth=self.user.auth)

        event = DownloadEvent.objects.get()
        assert event.size_bytes == 4096
        assert event.storage_region == self.node.osfstorage_region.name

    def test_zip_completed_is_unset_for_single_files(self):
        """Only zips stream through WaterButler, so nothing reports completion here."""
        self.app.get(f'/download/{self.guid}/', auth=self.user.auth)

        assert DownloadEvent.objects.get().zip_completed is None

    def test_anonymous_download_is_recorded_without_a_user(self):
        self.node.is_public = True
        self.node.save()

        self.app.get(f'/download/{self.guid}/')

        event = DownloadEvent.objects.get()
        assert event.user is None

    def test_mfr_render_is_not_recorded(self):
        self.app.get(f'/download/{self.guid}/?mode=render', auth=self.user.auth)

        assert not DownloadEvent.objects.exists()

    def test_download_still_succeeds_when_recording_fails(self):
        with pytest.MonkeyPatch.context() as patch:
            patch.setattr(
                'addons.base.views.record_download',
                lambda **kwargs: (_ for _ in ()).throw(ValueError('boom')),
            )
            res = self.app.get(f'/download/{self.guid}/', auth=self.user.auth)

        assert res.status_code == 302


class TestUserRegionDerivation:
    """The fallback chain, most to least trustworthy."""

    class FakeUser:
        def __init__(self, timezone):
            self.timezone = timezone

    def test_live_browser_timezone_wins(self):
        user = self.FakeUser('America/New_York')
        assert derive_user_region('Europe/Kyiv', user, 'Germany') == 'Europe/Kyiv'

    def test_falls_back_to_profile_timezone(self):
        user = self.FakeUser('America/New_York')
        assert derive_user_region('', user, 'Germany') == 'America/New_York'

    def test_default_profile_timezone_is_not_a_signal(self):
        """Every user has Etc/UTC until they change it, so it says nothing."""
        user = self.FakeUser('Etc/UTC')
        assert derive_user_region('', user, 'Germany') == 'Germany'

    def test_falls_back_to_storage_region(self):
        assert derive_user_region('', None, 'Germany') == 'Germany'

    def test_default_storage_region_is_not_a_signal(self):
        assert derive_user_region('', None, DEFAULT_REGION_NAME) == ''

    def test_unknown_is_empty(self):
        assert derive_user_region('', None, '') == ''


@pytest.mark.django_db
class TestRecordDownloadNeverRaises:

    def test_enqueue_failure_is_swallowed(self, monkeypatch):
        def explode(*args, **kwargs):
            raise ValueError('boom')

        monkeypatch.setattr('osf.utils.download_telemetry.enqueue_postcommit_task', explode)

        record_download(download_type=DownloadEvent.FILE, resource_guid='abcde')

        assert not DownloadEvent.objects.exists()

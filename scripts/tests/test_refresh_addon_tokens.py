from unittest import mock
from django.utils import timezone

from tests.base import OsfTestCase

from addons.box.tests.factories import BoxAccountFactory
from addons.googledrive.tests.factories import GoogleDriveAccountFactory
from addons.mendeley.tests.factories import MendeleyAccountFactory

import datetime

from dateutil.relativedelta import relativedelta

from website.oauth.models import ExternalAccount

from scripts.refresh_addon_tokens import (
    get_targets, main, look_up_provider, PROVIDER_CLASSES
)


class TestRefreshTokens(OsfTestCase):

    def setUp(self):
        super().setUp()
        self.addons = ('box', 'googledrive', 'mendeley', )

    def tearDown(self):
        super().tearDown()
        ExternalAccount.objects.all().delete()

    def test_look_up_provider(self):
        for Provider in PROVIDER_CLASSES:
            result = look_up_provider(Provider.short_name)
            assert result == Provider
        fake_result = look_up_provider('fake_addon_name')
        assert fake_result is None

    def test_get_targets(self):
        now = timezone.now()
        records = [
            BoxAccountFactory(date_last_refreshed=now - datetime.timedelta(days=4)),
            BoxAccountFactory(date_last_refreshed=now - datetime.timedelta(days=2)),
            GoogleDriveAccountFactory(date_last_refreshed=now - datetime.timedelta(days=4)),
            GoogleDriveAccountFactory(date_last_refreshed=now - datetime.timedelta(days=2)),
            MendeleyAccountFactory(date_last_refreshed=now - datetime.timedelta(days=4)),
            MendeleyAccountFactory(date_last_refreshed=now - datetime.timedelta(days=2)),
        ]
        box_targets = list(get_targets(delta=relativedelta(days=3), addon_short_name='box'))
        drive_targets = list(get_targets(delta=relativedelta(days=3), addon_short_name='googledrive'))
        mendeley_targets = list(get_targets(delta=relativedelta(days=3), addon_short_name='mendeley'))
        assert records[0]._id == box_targets[0]._id
        assert records[1] not in box_targets
        assert records[2]._id == drive_targets[0]._id
        assert records[3] not in drive_targets
        assert records[4]._id == mendeley_targets[0]._id
        assert records[5] not in mendeley_targets

    @mock.patch('scripts.refresh_addon_tokens.Mendeley.refresh_oauth_key')
    @mock.patch('scripts.refresh_addon_tokens.GoogleDriveProvider.refresh_oauth_key')
    @mock.patch('scripts.refresh_addon_tokens.Box.refresh_oauth_key')
    def test_refresh(self, mock_box_refresh, mock_drive_refresh, mock_mendeley_refresh):
        fake_authorized_box_account = BoxAccountFactory(date_last_refreshed=timezone.now())
        fake_authorized_drive_account = GoogleDriveAccountFactory(date_last_refreshed=timezone.now())
        fake_authorized_mendeley_account = MendeleyAccountFactory(date_last_refreshed=timezone.now())
        fake_unauthorized_box_account = BoxAccountFactory(date_last_refreshed=timezone.now() - datetime.timedelta(days=4))
        fake_unauthorized_drive_account = GoogleDriveAccountFactory(date_last_refreshed=timezone.now() - datetime.timedelta(days=4))
        fake_unauthorized_mendeley_account = MendeleyAccountFactory(date_last_refreshed=timezone.now() - datetime.timedelta(days=4))
        for addon in self.addons:
            Provider = look_up_provider(addon)
            main(delta=relativedelta(days=3), Provider=Provider, rate_limit=(5, 1), dry_run=False)
        assert 1 == mock_box_refresh.call_count
        assert 1 == mock_drive_refresh.call_count
        assert 1 == mock_mendeley_refresh.call_count

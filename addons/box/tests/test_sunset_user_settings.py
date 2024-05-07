import pytest
from waffle.testutils import override_flag
from osf import features
import unittest


from addons.base.tests.models import OAuthAddonUserSettingTestSuiteMixin
from addons.box.tests import factories


@pytest.mark.django_db
class TestBoxUserSettingsSunset(OAuthAddonUserSettingTestSuiteMixin, unittest.TestCase):
    full_name = 'Box'
    short_name = 'box'

    ExternalAccountFactory = factories.BoxAccountFactory

    def test_merge_user_settings(self):
        with override_flag(features.ENABLE_GV, active=True):
            super().test_merge_user_settings()

    def test_grant_oauth_access_no_metadata(self):
        with override_flag(features.ENABLE_GV, active=True):
            super().test_grant_oauth_access_no_metadata()

    def test_grant_oauth_access_metadata(self):
        with override_flag(features.ENABLE_GV, active=True):
            super().test_grant_oauth_access_metadata()

    def test_verify_oauth_access_no_metadata(self):
        with override_flag(features.ENABLE_GV, active=True):
            super().test_verify_oauth_access_no_metadata()

    def test_verify_oauth_access_metadata(self):
        with override_flag(features.ENABLE_GV, active=True):
            super().test_verify_oauth_access_metadata()

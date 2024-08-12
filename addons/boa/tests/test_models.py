import pytest
import unittest

from addons.base.exceptions import NotApplicableError
from addons.base.tests.models import (
    OAuthAddonNodeSettingsTestSuiteMixin,
    OAuthAddonUserSettingTestSuiteMixin,
)
from addons.boa.tests.utils import BoaAddonTestCaseBaseMixin
from framework.auth import Auth
from osf.models import NodeLog

pytestmark = pytest.mark.django_db


class TestUserSettings(
    BoaAddonTestCaseBaseMixin,
    OAuthAddonUserSettingTestSuiteMixin,
    unittest.TestCase,
):
    pass


class TestNodeSettings(
    BoaAddonTestCaseBaseMixin,
    OAuthAddonNodeSettingsTestSuiteMixin,
    unittest.TestCase,
):
    def test_set_folder(self):
        with pytest.raises(NotApplicableError):
            self.node_settings.set_folder(
                "fake_folder_id", auth=Auth(self.user)
            )

    def test_create_log(self):
        with pytest.raises(NotApplicableError):
            self.node_settings.create_waterbutler_log(
                auth=Auth(user=self.user),
                action=NodeLog.FILE_ADDED,
                metadata={
                    "path": "fake_path",
                    "materialized": "fake_materialized_path",
                },
            )

    def test_serialize_credentials(self):
        with pytest.raises(NotApplicableError):
            _ = self.node_settings.serialize_waterbutler_credentials()

    def test_serialize_settings(self):
        with pytest.raises(NotApplicableError):
            _ = self.node_settings.serialize_waterbutler_settings()

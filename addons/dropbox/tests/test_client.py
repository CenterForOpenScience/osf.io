import unittest

import pytest
from osf_tests.factories import UserFactory
from addons.dropbox.models import UserSettings

pytestmark = pytest.mark.django_db


class TestCore(unittest.TestCase):

    def setUp(self):

        super().setUp()

        self.user = UserFactory()
        self.user.add_addon('dropbox')
        self.user.save()

        self.settings = self.user.get_addon('dropbox')
        self.settings.access_token = '12345'
        self.settings.save()

    def test_get_addon_returns_dropbox_user_settings(self):
        result = self.user.get_addon('dropbox')
        assert isinstance(result, UserSettings)

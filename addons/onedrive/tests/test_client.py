# -*- coding: utf-8 -*-
import pytest
import unittest

from osf_tests.factories import UserFactory

from addons.onedrive.models import UserSettings

pytestmark = pytest.mark.django_db

class TestCore(unittest.TestCase):

    def setUp(self):
        super(TestCore, self).setUp()

        self.user = UserFactory()
        self.user.add_addon('onedrive')
        self.user.save()

        self.settings = self.user.get_addon('onedrive')
        self.settings.access_token = '12345'
        self.settings.save()

    def test_get_addon_returns_onedrive_user_settings(self):
        result = self.user.get_addon('onedrive')
        assert isinstance(result, UserSettings)



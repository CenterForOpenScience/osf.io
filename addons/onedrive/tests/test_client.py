# -*- coding: utf-8 -*-
import pytest

from osf_tests.factories import UserFactory

from addons.onedrive.models import UserSettings

pytestmark = pytest.mark.django_db

class TestCore:

    @pytest.fixture()
    def user(self):
        ret = UserFactory()
        ret.add_addon('onedrive')
        ret.save()
        return ret

    @pytest.fixture()
    def user_settings(self, user):
        settings = user.get_addon('onedrive')
        settings.access_token = '12345'
        settings.save()
        return settings

    def test_get_addon_returns_onedrive_user_settings(self, user_settings, user):
        result = user.get_addon('onedrive')
        assert isinstance(result, UserSettings)

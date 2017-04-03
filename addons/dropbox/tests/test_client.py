import unittest

import pytest
from nose.tools import assert_true  # noqa (PEP8 asserts)
from tests.factories import UserFactory
from addons.dropbox.models import UserSettings

pytestmark = pytest.mark.django_db


class TestCore(unittest.TestCase):

    def setUp(self):

        super(TestCore, self).setUp()

        self.user = UserFactory()
        self.user.add_addon('dropbox')
        self.user.save()

        self.settings = self.user.get_addon('dropbox')
        self.settings.access_token = '12345'
        self.settings.save()

    def test_get_addon_returns_dropbox_user_settings(self):
        result = self.user.get_addon('dropbox')
        assert_true(isinstance(result, UserSettings))

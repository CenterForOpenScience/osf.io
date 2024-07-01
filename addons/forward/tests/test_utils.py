"""Tests for addons.forward.utils."""

import pytest

from tests.base import OsfTestCase

from addons.forward.tests.factories import ForwardSettingsFactory
from addons.forward import utils

pytestmark = pytest.mark.django_db

class TestUtils(OsfTestCase):

    def test_serialize_settings(self):
        node_settings = ForwardSettingsFactory()
        serialized = utils.serialize_settings(node_settings)
        assert serialized == {
                'url': node_settings.url,
                'label': node_settings.label,
            }

    def test_settings_complete_true(self):
        node_settings = ForwardSettingsFactory()
        assert utils.settings_complete(node_settings)

    def test_settings_complete_true_no_redirect(self):
        """Regression test: Model can be complete when `redirect_bool` is False.

        """
        node_settings = ForwardSettingsFactory()
        assert not getattr(node_settings, 'redirect_bool', False)
        assert utils.settings_complete(node_settings)

    def test_settings_complete_false(self):
        node_settings = ForwardSettingsFactory(url=None)
        assert not utils.settings_complete(node_settings)

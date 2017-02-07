# -*- coding: utf-8 -*-
"""Tests for website.addons.forward.utils."""

from nose.tools import assert_equal, assert_true, assert_false
import pytest

from tests.base import OsfTestCase

from addons.forward.tests.factories import ForwardSettingsFactory
from addons.forward import utils

pytestmark = pytest.mark.django_db

class TestUtils(OsfTestCase):

    def test_serialize_settings(self):
        node_settings = ForwardSettingsFactory()
        serialized = utils.serialize_settings(node_settings)
        assert_equal(
            serialized,
            {
                'url': node_settings.url,
                'label': node_settings.label,
            }
        )

    def test_settings_complete_true(self):
        node_settings = ForwardSettingsFactory()
        assert_true(utils.settings_complete(node_settings))

    def test_settings_complete_true_no_redirect(self):
        """Regression test: Model can be complete when `redirect_bool` is False.

        """
        node_settings = ForwardSettingsFactory()
        assert_false(getattr(node_settings, 'redirect_bool', False))
        assert_true(utils.settings_complete(node_settings))

    def test_settings_complete_false(self):
        node_settings = ForwardSettingsFactory(url=None)
        assert_false(utils.settings_complete(node_settings))

# -*- coding: utf-8 -*-
"""Tests for website.addons.forward.utils."""

from nose.tools import *  # PEP8 asserts

from website.app import init_app

from website.addons.forward.tests.factories import ForwardSettingsFactory
from website.addons.forward import utils

app = init_app(set_backends=False, routes=True)


def test_serialize_settings():
    node_settings = ForwardSettingsFactory()
    serialized = utils.serialize_settings(node_settings)
    assert_equal(
        serialized,
        {
            'url': node_settings.url,
            'label': node_settings.label,
            'redirectBool': node_settings.redirect_bool,
            'redirectSecs': node_settings.redirect_secs,
        }
    )


def test_settings_complete_true():
    node_settings = ForwardSettingsFactory()
    assert_true(utils.settings_complete(node_settings))


def test_settings_complete_true_no_redirect():
    """Regression test: Model can be complete when `redirect_bool` is False.

    """
    node_settings = ForwardSettingsFactory(redirect_bool=False)
    assert_true(utils.settings_complete(node_settings))


def test_settings_complete_false():
    node_settings = ForwardSettingsFactory(url=None)
    assert_false(utils.settings_complete(node_settings))

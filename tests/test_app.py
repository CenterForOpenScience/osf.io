# -*- coding: utf-8 -*-
"""Unit tests for website.app."""

from nose.tools import *  # noqa (PEP8 asserts)
from flask import Flask

from tests.base import DbTestCase, assert_before

import framework
from website.app import attach_handlers
from website import settings



def test_attach_handlers():
    app = Flask(__name__)
    attach_handlers(app, settings)

    before_funcs = app.before_request_funcs[None]

    # Check that necessary handlers are attached
    assert_in(framework.sessions.prepare_private_key, before_funcs)
    assert_in(framework.sessions.before_request, before_funcs)
    if settings.USE_TOKU_MX:
        assert_in(framework.transactions.handlers.transaction_before_request, before_funcs)

    # Check that the order is correct
    assert_before(before_funcs, framework.sessions.prepare_private_key,
                framework.sessions.before_request)

    if settings.USE_TOKU_MX:
        assert_before(
            before_funcs,
            framework.transactions.handlers.transaction_before_request,
            framework.sessions.prepare_private_key
        )

# -*- coding: utf-8 -*-
"""Unit tests for website.app."""

from nose.tools import *  # noqa (PEP8 asserts)
from flask import Flask

import framework
from website.app import attach_handlers
from website import settings


def test_attach_handlers():
    app = Flask(__name__)
    attach_handlers(app, settings)

    before_funcs = app.before_request_funcs[None]
    after_funcs = app.after_request_funcs[None]
    teardown_funcs = app.teardown_request_funcs[None]

    assert_before_funcs = {
        framework.mongo.handlers.connection_before_request,
        framework.celery_tasks.handlers.celery_before_request,
        framework.transactions.handlers.transaction_before_request,
        framework.postcommit_tasks.handlers.postcommit_before_request,
        framework.sessions.prepare_private_key,
        framework.sessions.before_request,
    }

    assert_after_funcs = {
        framework.postcommit_tasks.handlers.postcommit_after_request,
        framework.celery_tasks.handlers.celery_after_request,
        framework.transactions.handlers.transaction_after_request,
        framework.sessions.after_request,
    }

    assert_teardown_funcs = {
        framework.mongo.handlers.connection_teardown_request,
        framework.celery_tasks.handlers.celery_teardown_request,
        framework.transactions.handlers.transaction_teardown_request,
    }

    # Check that necessary handlers are attached and correctly ordered
    assert_equal(sorted(set(before_funcs)), sorted(assert_before_funcs))
    assert_equal(sorted(set(after_funcs)), sorted(assert_after_funcs))
    assert_equal(sorted(set(teardown_funcs)), sorted(assert_teardown_funcs))

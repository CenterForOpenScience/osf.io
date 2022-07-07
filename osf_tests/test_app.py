# -*- coding: utf-8 -*-
"""Unit tests for website.app."""

import framework

from flask import Flask
from nose.tools import *  # noqa (PEP8 asserts)
from website import settings
from website.app import attach_handlers
from tests.base import OsfTestCase


class TestApp(OsfTestCase):

    def test_attach_handlers(self):
        app = Flask(__name__)
        attach_handlers(app, settings)

        before_funcs = app.before_request_funcs[None]
        after_funcs = app.after_request_funcs[None]
        teardown_funcs = app.teardown_request_funcs[None]

        assert_before_funcs = {
            framework.django.handlers.reset_django_db_queries_and_close_connections,
            framework.celery_tasks.handlers.celery_before_request,
            framework.transactions.handlers.transaction_before_request,
            framework.postcommit_tasks.handlers.postcommit_before_request,
            framework.sessions.prepare_private_key,
            framework.sessions.before_request,
            framework.csrf.handlers.before_request,
        }

        assert_after_funcs = {
            framework.django.handlers.close_old_django_db_connections,
            framework.postcommit_tasks.handlers.postcommit_after_request,
            framework.celery_tasks.handlers.celery_after_request,
            framework.transactions.handlers.transaction_after_request,
            framework.sessions.after_request,
            framework.csrf.handlers.after_request,
        }

        assert_teardown_funcs = {
            framework.django.handlers.close_old_django_db_connections,
            framework.celery_tasks.handlers.celery_teardown_request,
            framework.transactions.handlers.transaction_teardown_request,
        }

        # Check that necessary handlers are attached and correctly ordered
        assert_equal(set(before_funcs), assert_before_funcs)
        assert_equal(set(after_funcs), assert_after_funcs)
        assert_equal(set(teardown_funcs), assert_teardown_funcs)

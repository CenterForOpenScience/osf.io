# -*- coding: utf-8 -*-
from __future__ import absolute_import

import framework
import importlib
import json
import logging
import os
import threading
from collections import OrderedDict

import django
from api.caching import listeners  # noqa
from django.apps import apps
from framework.addons.utils import render_addon_capabilities
from framework.celery_tasks import handlers as celery_task_handlers
from framework.django import handlers as django_handlers
from framework.csrf import handlers as csrf_handlers
from framework.flask import add_handlers, app
# Import necessary to initialize the root logger
from framework.logging import logger as root_logger  # noqa
from framework.postcommit_tasks import handlers as postcommit_handlers
from framework.sentry import sentry
from framework.transactions import handlers as transaction_handlers
# Imports necessary to connect signals
from website.archiver import listeners  # noqa
from website.mails import listeners  # noqa
from website.notifications import listeners  # noqa
from website.identifiers import listeners  # noqa
from website.reviews import listeners  # noqa
from werkzeug.contrib.fixers import ProxyFix

logger = logging.getLogger(__name__)


def init_addons(settings, routes=True):
    """Initialize each addon in settings.ADDONS_REQUESTED.

    :param module settings: The settings module.
    :param bool routes: Add each addon's routing rules to the URL map.
    """
    settings.ADDONS_AVAILABLE = getattr(settings, 'ADDONS_AVAILABLE', [])
    settings.ADDONS_AVAILABLE_DICT = getattr(settings, 'ADDONS_AVAILABLE_DICT', OrderedDict())
    for addon_name in settings.ADDONS_REQUESTED:
        try:
            addon = apps.get_app_config('addons_{}'.format(addon_name))
        except LookupError:
            addon = None
        if addon:
            if addon not in settings.ADDONS_AVAILABLE:
                settings.ADDONS_AVAILABLE.append(addon)
            settings.ADDONS_AVAILABLE_DICT[addon.short_name] = addon
    settings.ADDON_CAPABILITIES = render_addon_capabilities(settings.ADDONS_AVAILABLE)

def attach_handlers(app, settings):
    """Add callback handlers to ``app`` in the correct order."""
    # Add callback handlers to application
    add_handlers(app, django_handlers.handlers)
    add_handlers(app, celery_task_handlers.handlers)
    add_handlers(app, transaction_handlers.handlers)
    add_handlers(app, postcommit_handlers.handlers)
    add_handlers(app, csrf_handlers.handlers)

    # Attach handler for checking view-only link keys.
    # NOTE: This must be attached AFTER the TokuMX to avoid calling
    # a commitTransaction (in toku's after_request handler) when no transaction
    # has been created
    add_handlers(app, {'before_request': framework.sessions.prepare_private_key})
    # framework.session's before_request handler must go after
    # prepare_private_key, else view-only links won't work
    add_handlers(app, {'before_request': framework.sessions.before_request,
                       'after_request': framework.sessions.after_request})

    return app


def setup_django():
    # Django App config
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'api.base.settings')
    django.setup()


def init_app(settings_module='website.settings', set_backends=True, routes=True,
             attach_request_handlers=True):
    """Initializes the OSF. A sort of pseudo-app factory that allows you to
    bind settings, set up routing, and set storage backends, but only acts on
    a single app instance (rather than creating multiple instances).

    :param settings_module: A string, the settings module to use.
    :param set_backends: Deprecated.
    :param routes: Whether to set the url map.

    """
    # Ensure app initialization only takes place once
    if app.config.get('IS_INITIALIZED', False) is True:
        return app

    logger.info('Initializing the application from process {}, thread {}.'.format(
        os.getpid(), threading.get_ident()
    ))
    setup_django()

    # The settings module
    settings = importlib.import_module(settings_module)

    init_addons(settings, routes)
    with open(os.path.join(settings.STATIC_FOLDER, 'built', 'nodeCategories.json'), 'wb') as fp:
        json.dump(settings.NODE_CATEGORY_MAP, fp)

    app.debug = settings.DEBUG_MODE

    # default config for flask app, however, this does not affect setting cookie using set_cookie()
    app.config['SESSION_COOKIE_SECURE'] = settings.SESSION_COOKIE_SECURE
    app.config['SESSION_COOKIE_HTTPONLY'] = settings.SESSION_COOKIE_HTTPONLY

    if routes:
        try:
            from website.routes import make_url_map
            make_url_map(app)
        except AssertionError:  # Route map has already been created
            pass

    if attach_request_handlers:
        attach_handlers(app, settings)

    if app.debug:
        logger.info("Sentry disabled; Flask's debug mode enabled")
    else:
        sentry.init_app(app)
        logger.info("Sentry enabled; Flask's debug mode disabled")

    apply_middlewares(app, settings)

    app.config['IS_INITIALIZED'] = True
    return app


def apply_middlewares(flask_app, settings):
    # Use ProxyFix to respect X-Forwarded-Proto header
    # https://stackoverflow.com/questions/23347387/x-forwarded-proto-and-flask
    if settings.LOAD_BALANCER:
        flask_app.wsgi_app = ProxyFix(flask_app.wsgi_app)

    return flask_app

# -*- coding: utf-8 -*-

import importlib

from modularodm import storage

import framework
from framework.flask import app, add_handlers
from framework.logging import logger
from framework.mongo import set_up_storage
from framework.addons.utils import render_addon_capabilities
from framework.sentry import sentry
from framework.mongo import handlers as mongo_handlers
from framework.transactions import handlers as transaction_handlers

import website.models
from website.routes import make_url_map
from website.addons.base import init_addon
from website.project.model import ensure_schemas


def init_addons(settings, routes=True):
    ADDONS_AVAILABLE = []
    for addon_name in settings.ADDONS_REQUESTED:
        addon = init_addon(app, addon_name, routes)
        if addon:
            ADDONS_AVAILABLE.append(addon)
    settings.ADDONS_AVAILABLE = ADDONS_AVAILABLE

    settings.ADDONS_AVAILABLE_DICT = {
        addon.short_name: addon
        for addon in settings.ADDONS_AVAILABLE
    }

    settings.ADDON_CAPABILITIES = render_addon_capabilities(settings.ADDONS_AVAILABLE)


def attach_handlers(app, settings):
    """Add callback handlers to ``app`` in the correct order."""
    # Add callback handlers to application
    add_handlers(app, mongo_handlers.handlers)
    if settings.USE_TOKU_MX:
        add_handlers(app, transaction_handlers.handlers)

    # Attach handler for checking view-only link keys.
    # NOTE: This must be attached AFTER the TokuMX to avoid calling
    # a commitTransaction (in toku's after_request handler) when no transaction
    # has been created
    add_handlers(app, {'before_request': framework.sessions.prepare_private_key})
    # framework.session's before_request handler must go after
    # prepare_private_key, else view-only links won't work
    add_handlers(app, {'before_request': framework.sessions.before_request})
    return app

def init_log_file(build_fp, settings):
    """Write header and core templates to the built log templates file."""
    build_fp.write('## Built templates file. DO NOT MODIFY.\n')
    with open(settings.CORE_TEMPLATES) as core_fp:
        # Exclude comments in core templates mako file
        content = '\n'.join([line.rstrip() for line in
            core_fp.readlines() if not line.strip().startswith('##')])
        build_fp.write(content)
    build_fp.write('\n')
    return None


def init_app(settings_module='website.settings', set_backends=True, routes=True):
    """Initializes the OSF. A sort of pseudo-app factory that allows you to
    bind settings, set up routing, and set storage backends, but only acts on
    a single app instance (rather than creating multiple instances).

    :param settings_module: A string, the settings module to use.
    :param set_backends: Whether to set the database storage backends.
    :param routes: Whether to set the url map.

    """
    # The settings module
    settings = importlib.import_module(settings_module)

    with open(settings.BUILT_TEMPLATES, 'w') as build_fp:
        init_log_file(build_fp, settings)

    try:
        init_addons(settings, routes)
    except AssertionError as error:  # Addon Route map has already been created
        logger.error(error)

    app.debug = settings.DEBUG_MODE
    if set_backends:
        logger.debug('Setting storage backends')
        set_up_storage(
            website.models.MODELS,
            storage.MongoStorage,
            addons=settings.ADDONS_AVAILABLE,
        )
    if routes:
        try:
            make_url_map(app)
        except AssertionError:  # Route map has already been created
            pass

    attach_handlers(app, settings)

    if app.debug:
        logger.info("Sentry disabled; Flask's debug mode enabled")
    else:
        sentry.init_app(app)
        logger.info("Sentry enabled; Flask's debug mode disabled")

    if set_backends:
        ensure_schemas()
    return app

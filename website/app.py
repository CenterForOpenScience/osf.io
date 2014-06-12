# -*- coding: utf-8 -*-
import importlib
import logging
import re

from framework import storage, db, app
from framework.mongo import set_up_storage
from framework.addons.utils import render_addon_capabilities
from framework.sentry import sentry
import website.models
from website.routes import make_url_map
from website.addons.base import init_addon

logger = logging.getLogger(__name__)

def init_addons(settings, routes=True):
    """

    """
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


def human_message(error):
    m = re.match(
        'View function mapping is overwriting an existing endpoint function: (.*)__(.*)',
        error.message)
    if not m:
        return None

    clobbered_renderer = m.group(1)
    clobbered_function = m.group(2)

    human_message = ' '.join(["You're trying to overwrite an existing",
                    "Flask endpoint with a renderer named `{}`".format(clobbered_renderer),
                    "and a view function named `{}`.".format(clobbered_function),
                    "You can't do that. Rename your view function or add a postfix."])
    return human_message


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
    try:
        init_addons(settings, routes)
    except AssertionError as error:  # Addon Route map has already been created
        logger.error(error)
        message = human_message(error)
        if message:
            logger.debug(human_message(error))

    app.debug = settings.DEBUG_MODE
    if set_backends:
        logger.debug('Setting storage backends')
        set_up_storage(
            website.models.MODELS, storage.MongoStorage,
            addons=settings.ADDONS_AVAILABLE, db=db
        )
    if routes:
        try:
            make_url_map(app)
        except AssertionError as error:  # Route map has already been created
            message = human_message(error)
            if message:
                logger.debug(message)



    if app.debug:
        logger.info("Sentry disabled; Flask's debug mode enabled")
    else:
        sentry.init_app(app)
        logger.info("Sentry enabled; Flask's debug mode disabled")

    return app

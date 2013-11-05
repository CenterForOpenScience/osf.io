# -*- coding: utf-8 -*-
import importlib
import logging

from framework import storage, db, app
from framework.mongo import set_up_storage
import website.models
from website.routes import make_url_map

logger = logging.getLogger(__name__)


def init_app(settings_module="website.settings", set_backends=True, routes=True):
    """Initializes the OSF. A sort of pseudo-app factory that allows you to
    bind settings, set up routing, and set storage backends, but only acts on
    a single app instance (rather than creating multiple instances).

    :param settings_module: A string, the settings module to use.
    :param set_backends: Whether to set the database storage backends.
    :param routes: Whether to set the url map.
    """
    # The settings module
    settings = importlib.import_module(settings_module)
    app.debug = settings.DEBUG_MODE
    if set_backends:
        # TODO: Instantiate client and db here?
        logger.debug("Setting storage backends")
        set_up_storage(website.models.MODELS, storage.MongoStorage, db=db)
    if routes:
        make_url_map(app)
    return app

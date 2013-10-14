#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging
import framework
from framework import set_up_storage, storage, db

import website.settings
import website.models
import website.routes

logger = logging.getLogger(__name__)

app = framework.app

static_folder = website.settings.static_path

import new_style  # Side effect: Sets up routes

# Set storage backend for all models to MongoDb
logger.debug("Setting storage backends")
set_up_storage(website.models.MODELS, storage.MongoStorage, db=db)

if __name__ == '__main__':
    app.run(port=5000)

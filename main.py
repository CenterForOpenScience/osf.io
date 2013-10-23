#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging
import framework
from framework import set_up_storage, storage, db

import website.settings
import website.models
import website.routes

# from website.addons.dataverse import route

app = framework.app

static_folder = website.settings.static_path

import new_style  # Side effect: Sets up routes

# Set storage backend for all models to MongoDb
logging.info("Setting storage backends")
set_up_storage(website.models.MODELS, storage.MongoStorage, db=db)

from website.project.model import ensure_schemas
ensure_schemas()

if __name__ == '__main__':
    app.run(port=5000)

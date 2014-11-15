# -*- coding: utf-8 -*-

from modularodm import storage

from framework.mongo import set_up_storage

from website import models


set_up_storage(models.MODELS, storage.MongoStorage)

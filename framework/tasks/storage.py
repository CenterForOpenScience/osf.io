# -*- coding: utf-8 -*-
"""Because Celery tasks are executed in a separate process, wwe must call
`set_up_storage` again here.
"""

from modularodm import storage

from framework.mongo import set_up_storage

from website import models


set_up_storage(models.MODELS, storage.MongoStorage)

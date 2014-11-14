# -*- coding: utf-8 -*-

from modularodm import storage

from framework.tasks import celery
from . import piwik


@celery.task(bind=True, max_retries=5, default_retry_delay=60)
def _update_node(self, node_id, updated_fields=None):
    # Avoid circular imports
    from framework.transactions.context import TokuTransaction
    from framework.mongo import set_up_storage
    from website import models
    # Attach schemas to database collections
    set_up_storage(models.MODELS, storage.MongoStorage)
    node = models.Node.load(node_id)
    # We may reach this task before the transaction that triggered it has been
    # committed, such that the target node does not yet exist in the database.
    if node is None:
        raise self.retry()
    try:
        with TokuTransaction():
            piwik._update_node_object(node, updated_fields)
    except Exception as error:
        raise self.retry(exc=error)


def update_node(node_id, updated_fields):
    _update_node.delay(node_id, updated_fields)

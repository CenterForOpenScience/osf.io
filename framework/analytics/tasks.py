# -*- coding: utf-8 -*-

from framework.tasks import celery
from framework.tasks.handlers import enqueue_task

from website import settings

from . import piwik


@celery.task(bind=True, max_retries=5, default_retry_delay=60)
def _update_node(self, node_id, updated_fields=None):
    # Avoid circular imports
    from framework.transactions.context import TokuTransaction
    from website import models
    node = models.Node.load(node_id)
    try:
        with TokuTransaction():
            piwik._update_node_object(node, updated_fields)
    except Exception as error:
        raise self.retry(exc=error)


def update_node(node_id, updated_fields):
    if settings.USE_CELERY:
        signature = _update_node.s(node_id, updated_fields)
        enqueue_task(signature)
    else:
        _update_node(node_id, updated_fields)

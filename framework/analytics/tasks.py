# -*- coding: utf-8 -*-

from framework.celery_tasks import app
from framework.celery_tasks.handlers import queued_task
from framework.transactions.context import transaction

from . import piwik


@queued_task
@app.task(bind=True, max_retries=5, default_retry_delay=60)
@transaction()
def update_user(self, user_id):
    from website import models
    user = models.User.load(user_id)
    try:
        piwik._create_user(user)
    except Exception as error:
        raise self.retry(exc=error)


@queued_task
@app.task(bind=True, max_retries=5, default_retry_delay=60)
@transaction()
def update_node(self, node_id, updated_fields=None):
    # Avoid circular imports
    from website import models
    node = models.Node.load(node_id)
    try:
        piwik._update_node_object(node, updated_fields)
    except Exception as error:
        raise self.retry(exc=error)

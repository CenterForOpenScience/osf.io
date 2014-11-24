# -*- coding: utf-8 -*-

import logging

from flask import g
from celery import group

from website import settings


logger = logging.getLogger(__name__)


def celery_before_request():
    g._celery_tasks = []


def celery_teardown_request(error=None):
    if error is not None:
        return
    try:
        tasks = g._celery_tasks
        if tasks:
            group(*tasks)()
    except AttributeError:
        if not settings.DEBUG_MODE:
            logger.error('Task queue not initialized')


def enqueue_task(signature):
    if signature not in g._celery_tasks:
        g._celery_tasks.append(signature)


handlers = {
    'before_request': celery_before_request,
    'teardown_request': celery_teardown_request,
}

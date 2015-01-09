# -*- coding: utf-8 -*-
"""Asynchronous task queue module."""

from celery import Celery
from celery.utils.log import get_task_logger

from raven import Client
from raven.contrib.celery import register_signal

from website import settings


app = Celery()

# TODO: Hardcoded settings module. Should be set using framework's config handler
app.config_from_object('website.settings')


if settings.SENTRY_DSN:
    client = Client(settings.SENTRY_DSN)
    register_signal(client)


@app.task
def error_handler(task_id, task_name):
    """logs detailed message about tasks that raise exceptions

    :param task_id: TaskID of the failed task
    :param task_name: name of task that failed
    """
    # get the current logger
    logger = get_task_logger(__name__)
    # query the broker for the AsyncResult
    result = app.AsyncResult(task_id)
    excep = result.get(propagate=False)
    # log detailed error mesage in error log
    logger.error('#####FAILURE LOG BEGIN#####\n'
                'Task {0} raised exception: {0}\n\{0}\n'
                '#####FAILURE LOG STOP#####'.format(task_name, excep, result.traceback))

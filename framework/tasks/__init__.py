# -*- coding: utf-8 -*-
'''Asynchronous task queue module.'''

from celery import Celery
from celery import current_app
from celery.utils.log import get_task_logger
from celery.signals import after_task_publish


# Adapted from http://stackoverflow.com/questions/9824172/find-out-whether-celery-task-exists
@after_task_publish.connect
def update_published_state(sender=None, body=None, **kwargs):
    """By default, Celery doesn't distinguish between tasks that are pending
    and tasks that have not been published; both are flagged as "PENDING". This
    callback sets task status to "PUBLISHED" after being sent to the message
    broker so that the application can determine which tasks are active.
    """
    # the task may not exist if sent using `send_task` which
    # sends tasks by name, so fall back to the default result backend
    # if that is the case.
    task = current_app.tasks.get(sender)
    backend = task.backend if task else current_app.backend
    backend.store_result(body['id'], None, 'PUBLISHED')


app = Celery()

# TODO: Hardcoded settings module. Should be set using framework's config handler
app.config_from_object('website.settings')

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

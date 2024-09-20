"""Asynchronous task queue module."""
from celery import Celery
from celery.utils.log import get_task_logger

from sentry_sdk import init, configure_scope
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.flask import FlaskIntegration

from website.settings import SENTRY_DSN, VERSION, CeleryConfig

app = Celery()
app.config_from_object(CeleryConfig)

if SENTRY_DSN:
    init(
        dsn=SENTRY_DSN,
        integrations=[CeleryIntegration(), DjangoIntegration(), FlaskIntegration()],
        release=VERSION,
    )
    with configure_scope() as scope:
        scope.set_tag('App', 'celery')


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
    logger.error(
        '#####FAILURE LOG BEGIN#####\n'
        f'Task {task_name} raised exception: {excep}\n{result.traceback}\n'
        '#####FAILURE LOG STOP#####'
    )

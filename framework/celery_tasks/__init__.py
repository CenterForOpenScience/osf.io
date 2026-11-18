"""Asynchronous task queue module."""
from celery import Celery
from celery.signals import beat_init, worker_init
from celery.utils.log import get_task_logger

from sentry_sdk import init, configure_scope
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.flask import FlaskIntegration

from website.settings import SENTRY_DSN, VERSION, CeleryConfig
from framework.celery_tasks import checks

app = Celery()
app.config_from_object(CeleryConfig)
# Make this app the fallback for celery.current_app in every thread, not only the importing one
app.set_default()

if SENTRY_DSN:
    init(
        dsn=SENTRY_DSN,
        integrations=[CeleryIntegration(), DjangoIntegration(), FlaskIntegration()],
        release=VERSION,
    )
    with configure_scope() as scope:
        scope.set_tag('App', 'celery')


@worker_init.connect
def check_routing(sender, **kwargs):
    """Sent once the worker has imported CeleryConfig.imports, so the registry has every task.
    """
    from framework import sentry

    tasks = checks.get_registered_tasks(sender.app)
    for message, found in (
        ('Tasks sent to the default queue without a route naming it',
         checks.find_tasks_sent_to_default_queue_implicitly(sender.app, tasks)),
        ('Routes to queues missing from CeleryConfig.task_queues',
         checks.find_routes_to_undeclared_queues(sender.app)),
        ('Routes matching no registered task',
         checks.find_routes_matching_no_task(sender.app, tasks)),
        ('Tasks setting routing attributes instead of using CeleryConfig.task_routes',
         checks.find_tasks_setting_routing_attributes(tasks)),
    ):
        if found:
            sentry.log_message(f'[Celery Config Check] {message}', skip_session=True, extra_data={'found': found})


@beat_init.connect
def check_periodic_tasks(sender, **kwargs):
    """Sent once beat has imported CeleryConfig.imports and synced CeleryConfig.beat_schedule to the database,
    so the enabled PeriodicTask rows are every entry beat will run.
    """
    from django_celery_beat.models import PeriodicTask
    from framework import sentry

    enabled = PeriodicTask.objects.enabled().values_list('name', 'task')
    unregistered = checks.find_periodic_tasks_with_unregistered_task(sender.app, enabled)
    if unregistered:
        sentry.log_message(
            '[Celery Config Check] Enabled periodic tasks running unregistered Celery tasks',
            skip_session=True,
            extra_data={'found': unregistered},
        )


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
    # log detailed error message in error log
    logger.error(
        '#####FAILURE LOG BEGIN#####\n'
        f'Task {task_name} raised exception: {excep}\n{result.traceback}\n'
        '#####FAILURE LOG STOP#####'
    )

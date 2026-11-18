"""Checks of the Celery routing and beat schedule, which framework.celery_tasks reports to Sentry when a worker or beat starts.

They run against the settings of the environment the process starts in, which the tests in
osf_tests/test_celery_routing.py don't see: e.g. a deployed local.py or the periodic tasks stored in the database.
"""
from fnmatch import fnmatchcase

# Set on the task itself (e.g. @app.task(queue=...)), these take precedence over task_routes
ROUTING_ATTRIBUTES = ('queue', 'exchange', 'routing_key')


def get_registered_tasks(app):
    return {name: task for name, task in app.tasks.items() if not name.startswith('celery.')}


def find_tasks_sent_to_default_queue_implicitly(app, tasks):
    # Celery silently sends a task to task_default_queue when no route matches it or its matching route
    # is empty or names no queue, so a task may only end up there when its route names that queue
    default_queue = app.conf.task_default_queue
    router = app.amqp.router
    implicit = []
    for name, task in sorted(tasks.items()):
        # Resolve the queue like Task.apply_async() does: the task's own options merged over its route
        queue = router.route(dict(task._get_exec_options()), name).get('queue')
        route = router.lookup_route(name) or {}
        if (queue is None or queue.name == default_queue) and route.get('queue') != default_queue:
            implicit.append(name)
    return implicit


def find_routes_to_undeclared_queues(app):
    # A queue missing from task_queues is created on send (task_create_missing_queues), with no worker consuming it
    declared = {queue.name for queue in app.conf.task_queues}
    return {
        entry: route.get('queue')
        for entry, route in app.conf.task_routes.items()
        if route.get('queue') not in declared
    }


def find_routes_matching_no_task(app, tasks):
    # Celery matches task_routes entries against task names as fnmatch globs, so an entry that
    # matches no registered task routes nothing: the task is gone, renamed, or not in CeleryConfig.imports
    return [
        entry for entry in app.conf.task_routes
        if not any(fnmatchcase(name, entry) for name in tasks)
    ]


def find_tasks_setting_routing_attributes(tasks):
    # Only catches routing set on the task decorator (e.g. @app.task(queue=...)). Overrides passed at call time,
    # e.g. task.apply_async(queue=...), live in the calling code and take precedence over both, but aren't visible here
    overrides = {}
    for name, task in sorted(tasks.items()):
        attributes = {attr: getattr(task, attr) for attr in ROUTING_ATTRIBUTES if getattr(task, attr, None) is not None}
        if attributes:
            overrides[name] = attributes
    return overrides


def find_periodic_tasks_with_unregistered_task(app, periodic_tasks):
    # periodic_tasks are (entry name, task name) pairs, e.g. from CeleryConfig.beat_schedule or the database.
    # Beat sends tasks by name, so otherwise an unregistered one is only noticed when a worker discards it
    return {name: task for name, task in periodic_tasks if task not in app.tasks}

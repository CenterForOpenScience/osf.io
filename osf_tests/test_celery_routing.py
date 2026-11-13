"""Tests for the Celery task routing configured in website.settings.CeleryConfig."""
import importlib
from fnmatch import fnmatchcase

import pytest

from framework.celery_tasks import app as celery_app

# Set on the task itself (e.g. @app.task(queue=...)), these take precedence over task_routes
ROUTING_ATTRIBUTES = ('queue', 'exchange', 'routing_key')


@pytest.fixture(scope='module')
def registered_tasks():
    # Register the tasks from CeleryConfig.imports like the worker does on start.
    # Not loader.import_default_modules(): Celery's Django fixup would also run the Django system checks
    for module in (*celery_app.conf.imports, *celery_app.conf.include):
        importlib.import_module(module)
    return {name: task for name, task in celery_app.tasks.items() if not name.startswith('celery.')}


def test_every_task_has_a_route(registered_tasks):
    # Celery silently sends a task to task_default_queue when no route matches it or its matching route
    # is empty or names no queue, so a task may only end up there when its route names that queue
    default_queue = celery_app.conf.task_default_queue
    router = celery_app.amqp.router
    implicit = []
    for name, task in sorted(registered_tasks.items()):
        # Resolve the queue like Task.apply_async() does: the task's own options merged over its route
        queue = router.route(dict(task._get_exec_options()), name).get('queue')
        route = router.lookup_route(name) or {}
        if (queue is None or queue.name == default_queue) and route.get('queue') != default_queue:
            implicit.append(name)
    assert not implicit, f'Tasks sent to the default queue without a route naming it: {implicit}'


def test_every_route_targets_a_declared_queue():
    # A queue missing from task_queues is created on send (task_create_missing_queues), with no worker consuming it
    declared = {queue.name for queue in celery_app.conf.task_queues}
    undeclared = {
        entry: route.get('queue', None)
        for entry, route in celery_app.conf.task_routes.items()
        if route.get('queue', None) not in declared
    }
    assert not undeclared, f'Routes to queues missing from CeleryConfig.task_queues: {undeclared}'


def test_every_route_matches_a_registered_task(registered_tasks):
    # Celery matches task_routes entries against task names as fnmatch globs, so an entry that
    # matches no registered task routes nothing: the task is gone, renamed, or not in CeleryConfig.imports
    unmatched = [
        entry for entry in celery_app.conf.task_routes
        if not any(fnmatchcase(name, entry) for name in registered_tasks)
    ]
    assert not unmatched, f'Routes matching no registered task: {unmatched}'


def test_no_task_sets_routing_attributes(registered_tasks):
    overrides = {}
    for name, task in sorted(registered_tasks.items()):
        attributes = {attr: getattr(task, attr) for attr in ROUTING_ATTRIBUTES if getattr(task, attr, None) is not None}
        if attributes:
            overrides[name] = attributes
    assert not overrides, f'Tasks setting routing attributes instead of using CeleryConfig.task_routes: {overrides}'

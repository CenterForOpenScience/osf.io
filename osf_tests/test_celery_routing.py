"""Tests for the Celery task routing and beat schedule configured in website.settings.CeleryConfig."""
import importlib

import pytest

from framework.celery_tasks import app as celery_app, checks


@pytest.fixture(scope='module')
def registered_tasks():
    # Register the tasks from CeleryConfig.imports like the worker does on start.
    # Not loader.import_default_modules(): Celery's Django fixup would also run the Django system checks
    for module in (*celery_app.conf.imports, *celery_app.conf.include):
        importlib.import_module(module)
    return checks.get_registered_tasks(celery_app)


def test_every_task_has_a_route(registered_tasks):
    implicit = checks.find_tasks_sent_to_default_queue_implicitly(celery_app, registered_tasks)
    assert not implicit, f'Tasks sent to the default queue without a route naming it: {implicit}'


def test_every_route_targets_a_declared_queue():
    undeclared = checks.find_routes_to_undeclared_queues(celery_app)
    assert not undeclared, f'Routes to queues missing from CeleryConfig.task_queues: {undeclared}'


def test_every_route_matches_a_registered_task(registered_tasks):
    unmatched = checks.find_routes_matching_no_task(celery_app, registered_tasks)
    assert not unmatched, f'Routes matching no registered task: {unmatched}'


def test_no_task_sets_routing_attributes(registered_tasks):
    overrides = checks.find_tasks_setting_routing_attributes(registered_tasks)
    assert not overrides, f'Tasks setting routing attributes instead of using CeleryConfig.task_routes: {overrides}'


@pytest.mark.usefixtures('registered_tasks')
def test_every_beat_schedule_entry_runs_a_registered_task():
    # Checked against all of celery_app.tasks
    # Entries may run Celery's built-in tasks, e.g. celery.backend_cleanup
    entries = ((name, entry['task']) for name, entry in celery_app.conf.beat_schedule.items())
    unregistered = checks.find_periodic_tasks_with_unregistered_task(celery_app, entries)
    assert not unregistered, f'CeleryConfig.beat_schedule entries running unregistered tasks: {unregistered}'

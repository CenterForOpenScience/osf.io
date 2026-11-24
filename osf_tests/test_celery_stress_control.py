from datetime import timedelta
from unittest.mock import Mock, patch

import pytest
from django.utils import timezone

from osf.models.celery_test import CeleryTestSuite as Suite, CeleryTestTask as Task
from osf.celery_stress_test import control, tasks
from osf.celery_stress_test.metrics import suite_metrics

pytestmark = pytest.mark.django_db

@pytest.fixture
def suite():
    return Suite.objects.create(config={
        'name': 'Test suite', 'total_duration': 1, 'max_total_rate': 10,
        'workloads': [{'name': 'I/O', 'mode': 'io', 'queue': 'celery', 'rate': 10,
                       'io_seconds': 0, 'cpu_iterations': None}],
    })

def make_task(suite, **kwargs):
    return Task.objects.create(suite=suite, workload_index=0, queue='celery', **kwargs)

def test_queued_cancellation_prevents_coordinator_and_workload_execution(suite):
    task = make_task(suite)
    app = Mock()
    control.cancel_suite(suite.id, None, app)
    tasks.start_celery_stress_test.run(str(suite.id))
    with patch.object(tasks.time, 'sleep') as sleep:
        tasks.simulated_workload.run(test_task_id=str(task.id))
    sleep.assert_not_called()
    suite.refresh_from_db()
    task.refresh_from_db()
    assert suite.status == Suite.Status.CANCELLED
    assert task.status == Task.Status.CANCELLED
    app.control.revoke.assert_any_call(str(suite.coordinator_task_id), terminate=False)
    app.control.revoke.assert_any_call([str(task.id)], terminate=False)

def test_cancellation_waits_for_running_tasks_and_coordinator(suite):
    suite.status, suite.started_at = Suite.Status.RUNNING, timezone.now()
    suite.save()
    task = make_task(suite, status=Task.Status.RUNNING, started_at=timezone.now())
    queued = make_task(suite)
    control.cancel_suite(suite.id, None, Mock())
    suite.refresh_from_db()
    queued.refresh_from_db()
    assert suite.status == Suite.Status.CANCELLING
    assert queued.status == Task.Status.CANCELLED
    control.finish_task(task.id, Task.Status.SUCCEEDED, runtime=.5)
    suite.refresh_from_db()
    assert suite.status == Suite.Status.CANCELLING
    control.finish_publishing(suite.id)
    suite.refresh_from_db()
    task.refresh_from_db()
    assert suite.status == Suite.Status.CANCELLED
    assert task.status == Task.Status.CANCELLED
    assert task.runtime_seconds == .5

def test_broker_failure_does_not_lose_cancel_request(suite):
    app = Mock()
    app.control.revoke.side_effect = OSError('Broker unavailable')
    _, warning = control.cancel_suite(suite.id, None, app)
    suite.refresh_from_db()
    assert warning
    assert suite.cancel_requested_at is not None
    assert suite.status == Suite.Status.CANCELLED

def test_publishing_finish_drains_before_completing(suite):
    task = make_task(suite)
    control.finish_publishing(suite.id)
    suite.refresh_from_db()
    assert suite.status == Suite.Status.DRAINING
    control.finish_task(task.id, Task.Status.SUCCEEDED, runtime=.1)
    suite.refresh_from_db()
    assert suite.status == Suite.Status.DRAINING
    control.finish_publishing(suite.id)
    suite.refresh_from_db()
    assert suite.status == Suite.Status.COMPLETED
    finished_at = suite.finished_at
    control.finish_task(task.id, Task.Status.FAILED, 'Duplicate delivery')
    suite.refresh_from_db()
    assert suite.finished_at == finished_at
    assert suite.status == Suite.Status.COMPLETED

def test_worker_failure_signal_finishes_orphaned_task(suite):
    task = make_task(suite, status=Task.Status.RUNNING, started_at=timezone.now())
    control.finish_publishing(suite.id)
    tasks.task_failure.send(
        sender=tasks.celery_app.tasks['stress_testing.scenario'],
        task_id=str(task.id), exception=RuntimeError('lost child'),
    )
    task.refresh_from_db()
    suite.refresh_from_db()
    assert task.status == Task.Status.FAILED
    assert suite.status == Suite.Status.DRAINING
    control.finish_publishing(suite.id)
    suite.refresh_from_db()
    assert suite.status == Suite.Status.FAILED

def test_coordinator_revoked_before_start(suite):
    tasks.record_test_revocation(request=Mock(name='unused', **{
        'id': str(suite.coordinator_task_id),
    }))  # Unknown task names do not affect the suite.
    request = Mock()
    request.name = 'stress_testing.start_celery_stress_test'
    request.id = str(suite.coordinator_task_id)
    tasks.task_revoked.send(
        sender=tasks.celery_app.tasks['stress_testing.start_celery_stress_test'], request=request,
    )
    suite.refresh_from_db()
    assert suite.status == Suite.Status.FAILED

def test_metrics_use_successful_samples_and_full_elapsed_time(suite):
    now = timezone.now()
    suite.started_at = now - timedelta(seconds=20)
    suite.publishing_finished_at = now - timedelta(seconds=10)
    suite.finished_at = now
    suite.status = Suite.Status.COMPLETED
    suite.save()
    for value in range(1, 21):
        make_task(suite, status=Task.Status.SUCCEEDED, wait_seconds=value, runtime_seconds=value / 10,
                  total_seconds=value * 2, published_at=now)
    make_task(suite, status=Task.Status.FAILED, runtime_seconds=1000)
    make_task(suite, status=Task.Status.CANCELLED, runtime_seconds=1000)
    result = suite_metrics(suite)
    assert result['total'] == 22
    assert result['published'] == 20
    assert result['publish_rate'] == 2
    assert result['throughput'] == 1
    assert result['wait']['p95'] == 19
    assert result['runtime']['mean'] == pytest.approx(1.05)
    assert result['runtime']['samples'] == 20
    assert result['failure_percent'] == pytest.approx(100 / 21)

def test_empty_metrics_and_repeated_cancellation(suite):
    assert suite_metrics(suite)['failure_percent'] is None
    assert suite_metrics(suite)['runtime']['p95'] is None
    control.cancel_suite(suite.id, None, Mock())
    suite.refresh_from_db()
    timestamp = suite.cancel_requested_at
    app = Mock()
    control.cancel_suite(suite.id, None, app)
    suite.refresh_from_db()
    assert suite.cancel_requested_at == timestamp
    app.control.revoke.assert_not_called()

@pytest.mark.parametrize('signal,receiver', [
    (tasks.task_failure, tasks.record_test_failure),
    (tasks.task_revoked, tasks.record_test_revocation),
])
def test_stress_signal_handlers_ignore_unrelated_tasks(signal, receiver):
    app = tasks.celery_app
    app.finalize()
    unrelated = app.tasks['celery.backend_cleanup']
    responses = signal.send(sender=unrelated, task_id='unrelated-id', request=None)
    assert receiver not in [handler for handler, _ in responses]

@pytest.mark.parametrize('task_name', [
    'stress_testing.scenario', 'stress_testing.start_celery_stress_test',
])
@pytest.mark.parametrize('signal,receiver', [
    (tasks.task_failure, tasks.record_test_failure),
    (tasks.task_revoked, tasks.record_test_revocation),
])
def test_concrete_stress_senders_are_registered_once(task_name, signal, receiver):
    app = tasks.celery_app
    app.finalize()
    # Covers the late-import path as well as duplicate registration attempts.
    tasks.register_test_signal_handlers(sender=app)
    tasks.register_test_signal_handlers(sender=app)
    task = app.tasks[task_name]
    responses = signal.send(sender=task, task_id=None, request=None)
    assert [handler for handler, _ in responses].count(receiver) == 1
    assert not [response for handler, response in responses if handler == receiver and isinstance(response, Exception)]

def test_signal_registration_runs_after_app_finalization():
    from celery import Celery

    app = Celery('stress-signal-registration', set_as_current=False)
    app.on_after_finalize.connect(tasks.register_test_signal_handlers)
    assert not app.finalized
    try:
        app.finalize()
        for name in ('stress_testing.scenario', 'stress_testing.start_celery_stress_test'):
            task = app.tasks[name]
            assert tasks.record_test_failure in tasks.task_failure._live_receivers(task)
            assert tasks.record_test_revocation in tasks.task_revoked._live_receivers(task)
    finally:
        for name in ('stress_testing.scenario', 'stress_testing.start_celery_stress_test'):
            task = app.tasks[name]
            tasks.task_failure.disconnect(sender=task, dispatch_uid=f'{name}.record_test_failure')
            tasks.task_revoked.disconnect(sender=task, dispatch_uid=f'{name}.record_test_revocation')
        app.close()

@pytest.mark.parametrize('task_name', ['stress_testing.scenario'])
def test_revocation_accepts_context_without_name(suite, task_name):
    from celery.app.task import Context
    task = make_task(suite)
    request = Context(id=str(task.id), task=task_name)
    assert not hasattr(request, 'name')
    tasks.task_revoked.send(sender=tasks.celery_app.tasks[task_name], request=request)
    task.refresh_from_db()
    assert task.status == Task.Status.CANCELLED
    assert task.error == 'Task revoked.'

def test_coordinator_revocation_accepts_context_without_name(suite):
    from celery.app.task import Context
    request = Context(id=str(suite.coordinator_task_id), task='stress_testing.start_celery_stress_test')
    tasks.record_test_revocation(request=request)
    suite.refresh_from_db()
    assert suite.status == Suite.Status.FAILED
    assert suite.error == 'Coordinator revoked.'

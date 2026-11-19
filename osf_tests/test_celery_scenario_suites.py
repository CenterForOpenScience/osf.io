from datetime import timedelta
from unittest.mock import patch, Mock

import pytest
from celery.exceptions import Retry
from celery import Celery, current_app
from celery.contrib.testing.worker import start_worker
from django.utils import timezone
from django.apps import apps
from django.db import connection
from django.test.utils import CaptureQueriesContext

from osf.celery_stress_test import control, scenarios, tasks
from osf.celery_stress_test.presets import resolve
from osf.celery_stress_test.metrics import suite_metrics
from osf.models.celery_test import CeleryTestSuite as Suite, CeleryTestTask as Task


pytestmark = pytest.mark.django_db


def make_suite(kind='retry'):
    return Suite.objects.create(config=resolve(kind, {}), started_at=timezone.now(), status='running')


def test_presets_are_snapshotted():
    config = resolve('retry', {'retry_delay': 5})
    config['queue'] = 'low'
    assert resolve('retry', {})['queue'] == 'celery'
    assert config['preset_version'] == 2


def test_retry_exhaustion_is_expected_failure():
    suite = make_suite()
    task = Task.objects.create(suite=suite, queue='celery', scenario='non_retryable',
                               expected={'failures': 1, 'attempts': 1, 'status': 'failed'})
    with pytest.raises(RuntimeError):
        scenarios.scenario_task.run(test_task_id=str(task.id))
    control.finish_publishing(suite.id)
    suite.refresh_from_db()
    assert suite.status == 'completed'
    assert suite.verdict == 'passed'
    assert task.attempts.get().outcome == 'failed'
    assert suite_metrics(suite)['failed'] == 1


def test_retry_is_nonterminal_and_cancelled():
    suite = make_suite()
    task = Task.objects.create(suite=suite, queue='celery', scenario='transient',
                               expected={'failures': 2, 'attempts': 3, 'status': 'succeeded'})
    with patch.object(scenarios.scenario_task, 'retry', side_effect=Retry()):
        with pytest.raises(Retry):
            scenarios.scenario_task.run(test_task_id=str(task.id))
    control.finish_publishing(suite.id)
    task.refresh_from_db()
    assert task.status == 'retrying'
    assert task.attempts.get().retry_at is not None
    control.cancel_suite(suite.id, None, Mock())
    task.refresh_from_db()
    assert task.status == 'cancelled'


def test_workflow_result_validation():
    suite = make_suite('workflow')
    task = Task.objects.create(suite=suite, queue='celery', scenario='callback', expected={'result': 6})
    assert scenarios.scenario_task.run([1, 2, 3], test_task_id=str(task.id)) == 6
    control.finish_publishing(suite.id)
    suite.refresh_from_db()
    assert suite.verdict == 'passed'


def test_deadline_finishes_missing_work():
    suite = make_suite('workflow')
    suite.deadline_at = timezone.now() - timedelta(seconds=1)
    suite.save()
    Task.objects.create(suite=suite, queue='celery', scenario='callback', expected={'result': 3})
    scenarios.reconcile_suites.run()
    suite.refresh_from_db()
    assert suite.verdict == 'failed'
    assert suite.finished_at
    assert 'deadline' in suite.error


def test_workflow_registers_all_steps_before_dispatch():
    suite = make_suite('workflow')
    with patch('celery.canvas.group.apply_async') as send, patch.object(scenarios, 'wait_for_tasks') as wait:
        send.side_effect = lambda **kwargs: None
        scenarios.publish_scenarios(suite.id, suite.config)
    wait.assert_called_once_with(suite.id, None)
    assert suite.tasks.count() == 9
    assert suite.tasks.filter(scenario__startswith='callback.').count() == 1


@pytest.mark.django_db(transaction=True, available_apps=[config.name for config in apps.get_app_configs()])
@pytest.mark.parametrize('kind', ['retry', 'workflow'])
def test_live_worker_executes_scenarios(kind):
    """Exercise real retries/canvas delivery without contacting the deployed broker."""
    previous_app = current_app._get_current_object()
    app = Celery('suite-integration', broker='memory://', backend='cache+memory://')
    app.conf.update(task_default_queue='celery', worker_hijack_root_logger=False)
    app.task(bind=True, name='stress_testing.scenario', ignore_result=False)(
        scenarios.scenario_task.run.__func__)
    app.set_current()
    try:
        suite = make_suite(kind)
        suite.status = Suite.Status.QUEUED
        suite.started_at = None
        suite.config['deadline_seconds'] = 15
        suite.config['retry_delay'] = 1
        suite.config.update({'tasks_per_scenario': 2} if kind == 'retry' else
                            {'workflow_count': 2, 'chain_length': 4, 'group_size': 4, 'chord_size': 5})
        suite.save()
        with start_worker(app, perform_ping_check=False, pool='solo', shutdown_timeout=10):
            tasks.start_celery_stress_test.run(str(suite.id))
            suite.refresh_from_db()
            assert suite.results['progress']['active'] == 0
            assert suite.heartbeat_at is not None
            assert suite.verdict == 'passed', (suite.error, suite.results)
    finally:
        previous_app.set_current()
        app.close()


def test_duplicate_callback_invalidates_verdict():
    suite = make_suite('workflow')
    task = Task.objects.create(suite=suite, queue='celery', scenario='callback', expected={'result': 3})
    scenarios.scenario_task.run([1, 2], test_task_id=str(task.id))
    scenarios.scenario_task.run([1, 2], test_task_id=str(task.id))
    control.finish_publishing(suite.id)
    suite.refresh_from_db()
    assert suite.verdict == 'failed'
    task.refresh_from_db()
    assert task.observations['callback_count'] == 2


def test_custom_workflow_sizes_and_expected_results():
    suite = make_suite('workflow')
    suite.config.update(workflow_count=2, chain_length=5, group_size=4, chord_size=6)
    with patch('celery.canvas.group.apply_async'), patch.object(scenarios, 'wait_for_tasks'):
        scenarios.publish_scenarios(suite.id, suite.config)
    assert suite.tasks.count() == 32
    assert suite.tasks.get(scenario='chain.0.4').expected['result'] == 20
    assert suite.tasks.get(scenario='callback.1').expected['result'] == 15


def test_scenario_worker_locks_only_its_task_and_leaves_suite_for_coordinator():
    suite = make_suite('workflow')
    task = Task.objects.create(suite=suite, queue='celery', scenario='chain.0', expected={'value': 2, 'result': 2})
    with CaptureQueriesContext(connection) as queries:
        assert scenarios.scenario_task.run(test_task_id=str(task.id)) == 2
    locked = [query['sql'] for query in queries if 'FOR UPDATE' in query['sql']]
    assert locked
    assert all('osf_celerytestsuite' not in sql for sql in locked)
    assert not any(query['sql'].startswith('UPDATE "osf_celerytestsuite"') for query in queries)
    suite.refresh_from_db()
    assert suite.status == Suite.Status.RUNNING
    assert suite.results == {}
    assert task.attempts.get().outcome == 'succeeded'


def test_coordinator_syncs_retry_progress_then_finalizes():
    suite = make_suite()
    suite.deadline_at = timezone.now() + timedelta(seconds=30)
    suite.save()
    task = Task.objects.create(suite=suite, queue='celery', scenario='transient', status='retrying',
                               expected={'status': 'succeeded', 'result': 0})

    def finish_on_next_poll(seconds):
        suite.refresh_from_db()
        assert suite.results['progress']['retrying'] == 1
        assert suite.results['progress']['active'] == 1
        assert suite.finished_at is None
        control.finish_task(task.id, Task.Status.SUCCEEDED, result=0)
        suite.refresh_from_db()
        assert suite.finished_at is None

    with patch.object(control.time, 'sleep', side_effect=finish_on_next_poll) as sleep:
        control.wait_for_tasks(suite.id)
    sleep.assert_called_once_with(5)
    control.finish_publishing(suite.id)
    suite.refresh_from_db()
    assert suite.verdict == Suite.Verdict.PASSED
    assert suite.results['progress']['succeeded'] == 1
    assert suite.results['progress']['active'] == 0


def test_late_callback_does_not_rewrite_final_suite():
    suite = make_suite('workflow')
    task = Task.objects.create(suite=suite, queue='celery', scenario='callback', expected={'result': 3})
    scenarios.scenario_task.run([1, 2], test_task_id=str(task.id))
    control.finish_publishing(suite.id)
    suite.refresh_from_db()
    results = suite.results
    finished = suite.finished_at
    scenarios.scenario_task.run([1, 2], test_task_id=str(task.id))
    suite.refresh_from_db()
    task.refresh_from_db()
    assert task.observations['callback_count'] == 2
    assert suite.results == results
    assert suite.finished_at == finished
    assert suite.verdict == Suite.Verdict.PASSED


@pytest.mark.parametrize('publication_error', [None, OSError('Broker disconnected')])
def test_coordinator_deadline_finishes_missing_workflow_steps(publication_error):
    suite = make_suite('workflow')
    suite.status = Suite.Status.QUEUED
    suite.deadline_at = timezone.now() - timedelta(seconds=1)
    suite.save()
    with patch('celery.canvas.group.apply_async', side_effect=publication_error):
        with pytest.raises(RuntimeError, match='deadline exceeded'):
            tasks.start_celery_stress_test.run(str(suite.id))
    suite.refresh_from_db()
    assert suite.status == Suite.Status.FAILED
    assert suite.results['progress']['failed'] == 9
    assert suite.results['progress']['active'] == 0
    if publication_error is not None:
        assert 'Broker disconnected' in suite.error


def test_cancellation_saves_final_progress_for_delayed_retries():
    suite = make_suite()
    suite.publishing_finished_at = timezone.now()
    suite.results = {'progress': {'retrying': 1, 'active': 1}}
    suite.save()
    Task.objects.create(suite=suite, queue='celery', scenario='transient', status=Task.Status.RETRYING)
    control.cancel_suite(suite.id, None, Mock())
    suite.refresh_from_db()
    assert suite.status == Suite.Status.CANCELLED
    assert suite.results['progress']['active'] == 0
    assert suite.results['progress']['cancelled'] == 1

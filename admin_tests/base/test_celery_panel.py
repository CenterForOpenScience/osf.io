from unittest.mock import Mock, patch
import pytest
from django.test import RequestFactory
from django.urls import reverse
from django.core.exceptions import PermissionDenied

from admin.base import celery_panel
from admin.base.forms import WorkloadForm, CeleryScenarioForm, CeleryStressTestForm
from osf.celery_stress_test.presets import resolve
from osf.models.celery_test import CeleryTestSuite as Suite, CeleryTestTask as Task
from website import settings

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

@pytest.fixture
def admin_views(settings):
    settings.ROOT_URLCONF = 'admin.base.urls'
    return celery_panel


def admin_request(method='get', data=None):
    request = getattr(RequestFactory(), method)('/suites/', data or {})
    request.user = Mock(is_authenticated=True, is_staff=True, is_active=True, is_superuser=True)
    return request

def test_dashboard_lists_active_before_finished_and_renders_actions(suite, admin_views):
    Suite.objects.create(name='Finished suite', config=suite.config, status=Suite.Status.COMPLETED)
    with patch.object(admin_views.panel_config, 'get_context', return_value={}):
        response = admin_views.celery_stress_suites(admin_request())
    html = response.content.decode()
    assert html.index('Celery load test') < html.index('Finished suite')
    assert 'Cancel suite' in html
    assert 'New test suite' in html

def test_detail_renders_config_outcomes_latency_and_errors(suite, admin_views):
    make_task(suite, status=Task.Status.FAILED, error='<script>error</script>')
    with patch.object(admin_views.panel_config, 'get_context', return_value={}):
        response = admin_views.celery_stress_suite_detail(admin_request(), suite.id)
    html = response.content.decode()
    assert 'Successful task latency' in html
    assert 'Submission to start' in html
    assert 'I/O / io / celery' in html
    assert '&lt;script&gt;error&lt;/script&gt;' in html
    assert '<script>error</script>' not in html

def test_cancel_is_post_only_and_permission_protected(suite, admin_views):
    request = admin_request()
    assert admin_views.celery_stress_suite_cancel(request, suite.id).status_code == 405
    request = admin_request('post')
    request.user.is_superuser = request.user.is_staff = False
    with pytest.raises(PermissionDenied):
        admin_views.celery_stress_suite_cancel(request, suite.id)
    suite.refresh_from_db()
    assert suite.cancel_requested_at is None

def test_create_committed_suite_before_broker_dispatch(admin_views):
    request = admin_request('post', {
        'name': 'New suite', 'total_duration': 1, 'drain_timeout': 120, 'max_total_rate': 10,
        'form-TOTAL_FORMS': '1', 'form-INITIAL_FORMS': '0',
        'form-0-name': 'I/O', 'form-0-mode': 'io', 'form-0-queue': 'celery',
        'form-0-rate': '1', 'form-0-io_seconds': '0',
    })
    request.user = None  # The auth decorator is bypassed only for this handler test.

    def dispatch(*args, **kwargs):
        assert Suite.objects.filter(pk=kwargs['args'][0]).exists()
        return Mock()
    with patch.object(admin_views.panel_config, 'get_context', return_value={}), \
            patch.object(admin_views.start_celery_stress_test, 'apply_async', side_effect=dispatch) as publish, \
            patch.object(admin_views.messages, 'success'):
        response = admin_views.celery_stress_test_view.__wrapped__.__wrapped__(request)
    assert response.status_code == 302
    assert publish.call_count == 1
    assert 'default' in admin_views.celery_stress_test_view._non_atomic_requests
    assert 'default' in admin_views.celery_stress_suite_cancel._non_atomic_requests

def test_create_form_renders_name_and_contiguous_form_prefix(admin_views):
    with patch.object(admin_views.panel_config, 'get_context', return_value={}):
        response = admin_views.celery_stress_test_view(admin_request())
    html = response.content.decode()
    assert 'name="name"' in html
    assert 'name="form-0-mode"' in html
    assert 'value.replace(/form-' in html

@pytest.mark.parametrize('preset', ['retry', 'workflow'])
def test_scenario_preset_form_renders(admin_views, preset):
    request = admin_request()
    request.GET = {'preset': preset}
    with patch.object(admin_views.panel_config, 'get_context', return_value={}):
        response = admin_views.celery_stress_test_view(request)
    html = response.content.decode()
    assert f'value="{preset}"' in html
    assert 'name="deadline_seconds"' in html
    assert ('name="retry_delay"' in html) == (preset == 'retry')
    assert ('name="chain_length"' in html) == (preset == 'workflow')

def test_unknown_preset_is_rejected(admin_views):
    request = admin_request()
    request.GET = {'preset': 'unknown'}
    with patch.object(admin_views.panel_config, 'get_context', return_value={}):
        assert admin_views.celery_stress_test_view(request).status_code == 400

def test_manual_reconciliation_is_post_only(admin_views):
    with patch.object(admin_views.reconcile_suites, 'run') as reconcile:
        assert admin_views.celery_stress_suites_reconcile(admin_request()).status_code == 405
    reconcile.assert_not_called()

def test_manual_reconciliation_runs_and_redirects(admin_views):
    with patch.object(admin_views.reconcile_suites, 'run') as reconcile, \
            patch.object(admin_views.messages, 'success'):
        response = admin_views.celery_stress_suites_reconcile(admin_request('post'))
    reconcile.assert_called_once_with()
    assert response.status_code == 302
    assert response.url == reverse('celery_stress_test')

def test_manual_reconciliation_requires_permission(admin_views):
    request = admin_request('post')
    request.user.is_superuser = request.user.is_staff = False
    with patch.object(admin_views.reconcile_suites, 'run') as reconcile:
        with pytest.raises(PermissionDenied):
            admin_views.celery_stress_suites_reconcile(request)
    reconcile.assert_not_called()

@pytest.mark.parametrize('overrides,field', [
    ({'workflow_count': 100, 'chain_length': 100}, 'workflow_count'),
    ({'chain_length': 1}, 'chain_length'),
])
def test_workflow_form_limits(overrides, field):
    data = resolve('workflow', {'name': 'Custom', **overrides})
    form = CeleryScenarioForm(data, suite_type='workflow')
    assert not form.is_valid()
    assert field in form.errors

def test_retry_form_requires_recoverable_transient_case():
    form = CeleryScenarioForm(resolve('retry', {'name': 'Custom', 'transient_failures': 4}), suite_type='retry')
    assert not form.is_valid()
    assert 'transient_failures' in form.errors


def test_queue_allowlist_is_shared_and_configurable(monkeypatch):
    monkeypatch.setattr(settings, 'CELERY_STRESS_TEST_QUEUES', ('low', 'unknown'))
    assert WorkloadForm().fields['queue'].choices == [('low', 'low')]
    assert CeleryScenarioForm(suite_type='retry').fields['queue'].choices == [('low', 'low')]


def test_load_submission_sets_deadline_and_rejects_large_run(admin_views):
    assert 'drain_timeout' in CeleryStressTestForm().fields
    request = admin_request('post', {
        'name': 'Too large', 'total_duration': 3600, 'drain_timeout': 120, 'max_total_rate': 1000,
        'form-TOTAL_FORMS': '1', 'form-INITIAL_FORMS': '0',
        'form-0-name': 'I/O', 'form-0-mode': 'io', 'form-0-queue': 'celery',
        'form-0-rate': '1000', 'form-0-io_seconds': '0',
    })
    with patch.object(admin_views.panel_config, 'get_context', return_value={}), \
            patch.object(admin_views.start_celery_stress_test, 'apply_async') as dispatch:
        response = admin_views.celery_stress_test_view(request)
    assert 'task limit' in response.content.decode()
    dispatch.assert_not_called()

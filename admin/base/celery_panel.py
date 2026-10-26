from collections import defaultdict
from functools import cache

from django.contrib import messages
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods
from dj_celery_panel import views
from dj_celery_panel.celery_utils import CeleryQueuesInspectBackend, QueueDetailPage, QueueListPage
from dj_celery_panel.conf import panel_config

from framework.celery_tasks import app as celery_app
from website.settings import CeleryConfig
from osf.celery_stress_test.tasks import start_celery_stress_test
from .forms import CeleryStressTestForm, WorkloadForm
from django.forms import formset_factory


WorkloadFormSet = formset_factory(
    WorkloadForm,
    extra=1,
    can_delete=True,
    max_num=10,
    min_num=1,
    validate_max=True,
)


@cache
def import_task_modules():
    # Register the tasks from CeleryConfig.imports like the worker does on start. Not in AppConfig.ready():
    # some task modules call django.setup() on import, which can't run while Django is loading apps
    celery_app.loader.import_default_modules()


def overview(request):
    # The overview lists the tasks registered in this process
    import_task_modules()
    return views.index(request)


class RoutedTasksQueuesBackend(CeleryQueuesInspectBackend):
    """dj-celery-panel queues backend that also lists the tasks routed to each queue, the
    CeleryConfig routing entries that match no task, and the configured queues that no active worker consumes.

    Routes are resolved the same way Celery does when sending a task, so explicit
    queue= overrides passed to apply_async() at call time are not reflected.
    """

    BACKEND_DESCRIPTION = 'Queue bindings, routing configuration, routed tasks, unmatched routing entries and unconsumed queues'

    def get_queues(self):
        page = super().get_queues()
        # Workers report only the queues they consume, so a configured queue nobody consumes
        # would be missing from the list while tasks routed to it pile up
        listed = {queue['name'] for queue in page.queues}
        unconsumed = [
            self.describe_unconsumed_queue(queue)
            for name, queue in sorted(self.app.amqp.queues.items())
            if name not in listed
        ]
        routed_tasks = self.get_routed_tasks_by_queue()
        unmatched_entries = self.get_unmatched_routing_entries_by_queue()
        return QueueListPage(
            queues=[
                {
                    **queue,
                    'routed_tasks_count': len(routed_tasks[queue['name']]),
                    'unmatched_routing_entries': unmatched_entries[queue['name']],
                }
                for queue in page.queues + unconsumed
            ],
            error=page.error,
        )

    def get_queue_detail(self, queue_name):
        page = super().get_queue_detail(queue_name)
        queue = page.queue
        if queue is None:
            # membership check first: indexing Queues creates missing ones
            if queue_name not in self.app.amqp.queues:
                return page
            queue = self.describe_unconsumed_queue(self.app.amqp.queues[queue_name])
        return QueueDetailPage(
            queue={**queue, 'routed_tasks': self.get_routed_tasks(queue_name)},
            error=page.error,
        )

    def describe_unconsumed_queue(self, queue):
        broker_info = self._get_queue_length_from_broker(queue.name)
        return {
            'name': queue.name,
            'exchange': queue.exchange.name,
            'exchange_type': queue.exchange.type,
            'routing_key': queue.routing_key,
            'durable': queue.durable,
            'auto_delete': queue.auto_delete,
            'exclusive': queue.exclusive,
            'arguments': queue.queue_arguments,
            'workers': [],
            'worker_details': [],
            'message_count': broker_info.get('length'),
            'consumer_count': broker_info.get('consumer_count'),
            'broker_query_error': broker_info.get('error'),
        }

    def get_routed_tasks(self, queue_name):
        return self.get_routed_tasks_by_queue()[queue_name]

    def get_registered_tasks(self):
        # Every task the worker registers, not only the ones this process happened to import
        import_task_modules()
        return {name: task for name, task in self.app.tasks.items() if not name.startswith('celery.')}

    def get_routed_tasks_by_queue(self):
        router = self.app.amqp.router
        routed_tasks = defaultdict(list)
        for name, task in sorted(self.get_registered_tasks().items()):
            routed_tasks[router.route(dict(task._get_exec_options()), name)['queue'].name].append(name)
        return routed_tasks

    def get_unmatched_routing_entries_by_queue(self):
        # CeleryRouter matches the dotted prefixes of a task name, from two parts up, against the CeleryConfig
        # *_modules sets, so an entry that is no such prefix of any registered task name routes nothing:
        # the task is gone, renamed, or its module isn't in CeleryConfig.imports.
        # An entry is listed under the queue that its exact name routes to
        prefixes = set()
        for name in self.get_registered_tasks():
            parts = name.split('.')
            prefixes.update('.'.join(parts[:i]) for i in range(2, len(parts) + 1))
        router = self.app.amqp.router
        unmatched_entries = defaultdict(list)
        # dir(), not vars(): the sets are defined on defaults.CeleryConfig, which local.py's CeleryConfig subclasses
        for attr in dir(CeleryConfig):
            if attr.endswith('_modules'):
                for entry in sorted(set(getattr(CeleryConfig, attr)) - prefixes):
                    unmatched_entries[router.route({}, entry)['queue'].name].append(entry)
        return unmatched_entries


@panel_config.permission_required('celery_stress_test')
@require_http_methods(['GET', 'POST'])
def celery_stress_test_view(request):
    """
    Configure and start a Celery stress test.
    """
    context = panel_config.get_context(
        request,
        current_tab='celery_stress_test',
    )

    if request.method == 'POST':
        form = CeleryStressTestForm(request.POST)
        workload_formset = WorkloadFormSet(request.POST)

        if form.is_valid() and workload_formset.is_valid():
            config = {
                **form.cleaned_data,
                'workloads': [
                    workload_form.cleaned_data
                    for workload_form in workload_formset
                    if workload_form.cleaned_data
                    and not workload_form.cleaned_data.get('DELETE', False)
                ],
            }

            if not config['workloads']:
                messages.error(
                    request,
                    'Please configure at least one workload.',
                )
            else:
                try:
                    result = start_celery_stress_test.delay(config)
                except Exception:
                    messages.error(
                        request,
                        'Failed to start the stress test. Please try again.',
                    )
                else:
                    messages.success(
                        request,
                        f"Stress test submitted successfully. Task ID: {result.id}",
                    )
                    return redirect(request.path)
    else:
        form = CeleryStressTestForm()
        workload_formset = WorkloadFormSet()

    context.update({
        'form': form,
        'workload_formset': workload_formset,
    })

    return render(
        request,
        'admin/dj_celery_panel/celery_stress_testing.html',
        context,
    )

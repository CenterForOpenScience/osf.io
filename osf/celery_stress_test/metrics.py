import math

from django.db.models import Avg, Count, Q
from django.utils import timezone

from osf.models.celery_test import CeleryTestTask as Task


def latency(tasks, field):
    """Summarize a timing field using successful tasks with recorded samples."""
    samples = tasks.filter(status=Task.Status.SUCCEEDED, **{f'{field}__isnull': False})
    summary = samples.aggregate(count=Count('id'), mean=Avg(field))
    p95 = None
    if summary['count']:
        p95 = samples.order_by(field).values_list(field, flat=True)[math.ceil(summary['count'] * .95) - 1]
    return {'mean': summary['mean'], 'p95': p95, 'samples': summary['count']}


def task_metrics(tasks, publish_seconds, elapsed_seconds):
    """Calculate task outcomes and rates over the supplied suite time windows."""
    counts = tasks.aggregate(**{
        status: Count('id', filter=Q(status=status)) for status in Task.Status.values
    })
    published = tasks.filter(published_at__isnull=False).count()
    attempted = counts['succeeded'] + counts['failed']
    return {
        **counts,
        'total': sum(counts.values()),
        'published': published,
        'publish_rate': published / publish_seconds if publish_seconds > 0 else None,
        'throughput': counts['succeeded'] / elapsed_seconds if elapsed_seconds > 0 else None,
        'failure_percent': counts['failed'] * 100 / attempted if attempted else None,
        'wait': latency(tasks, 'wait_seconds'),
        'runtime': latency(tasks, 'runtime_seconds'),
        'total_latency': latency(tasks, 'total_seconds'),
    }


def suite_metrics(suite):
    """Build suite and per-workload metrics for the admin detail page."""
    now = timezone.now()
    publish_seconds = ((suite.publishing_finished_at or now) - suite.started_at).total_seconds() if suite.started_at else 0
    elapsed = ((suite.finished_at or now) - suite.started_at).total_seconds() if suite.started_at else 0
    workloads = []
    for index, workload in enumerate(suite.config.get('workloads', [])):
        workloads.append({
            'config': workload,
            **task_metrics(suite.tasks.filter(workload_index=index), publish_seconds, elapsed),
        })
    return {
        **task_metrics(suite.tasks.all(), publish_seconds, elapsed),
        'workloads': workloads,
        'publishing_seconds': publish_seconds,
        'elapsed_seconds': elapsed,
        'requested_rate': sum(workload['rate'] for workload in suite.config.get('workloads', [])),
        'effective_rate_cap': min(suite.config.get('max_total_rate', 0), sum(workload['rate'] for workload in suite.config.get('workloads', []))),
        'workers': suite.tasks.exclude(worker='').values_list('worker', flat=True).distinct(),
    }

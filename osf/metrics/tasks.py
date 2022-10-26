from framework.celery_tasks import app as celery_app
from osf.metrics.counted_usage import CountedUsage


@celery_app.task(bind=True, max_retries=5, default_retry_delay=60)
def record_counted_usage(self, record_kwargs):
    try:
        CountedUsage.record(**record_kwargs)
    except Exception as exc:
        self.retry(exc=exc)

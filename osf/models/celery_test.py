import uuid

from django.db import models
from django.utils import timezone


class CeleryTestSuite(models.Model):
    class Status(models.TextChoices):
        QUEUED = 'queued', 'Queued'
        RUNNING = 'running', 'Publishing'
        DRAINING = 'draining', 'Draining'
        CANCELLING = 'cancelling', 'Cancelling'
        COMPLETED = 'completed', 'Completed'
        FAILED = 'failed', 'Failed'
        CANCELLED = 'cancelled', 'Cancelled'

    class Verdict(models.TextChoices):
        PENDING = 'pending', 'Pending'
        PASSED = 'passed', 'Passed'
        FAILED = 'failed', 'Failed'
        CANCELLED = 'cancelled', 'Cancelled'

    ACTIVE_STATUSES = (Status.QUEUED, Status.RUNNING, Status.DRAINING, Status.CANCELLING)
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_by = models.ForeignKey('OSFUser', null=True, blank=True, on_delete=models.SET_NULL)
    name = models.CharField(max_length=100, default='Celery load test')
    config = models.JSONField()
    verdict = models.CharField(max_length=16, choices=Verdict.choices, default=Verdict.PENDING)
    results = models.JSONField(default=dict)
    deadline_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.QUEUED, db_index=True)
    coordinator_task_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    created_at = models.DateTimeField(default=timezone.now)
    started_at = models.DateTimeField(null=True, blank=True)
    heartbeat_at = models.DateTimeField(null=True, blank=True)
    publishing_finished_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    cancel_requested_at = models.DateTimeField(null=True, blank=True)
    cancelled_by = models.ForeignKey('OSFUser', null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    error = models.TextField(blank=True)

    class Meta:
        ordering = ['-created_at']

    @property
    def is_active(self):
        return self.status in self.ACTIVE_STATUSES

    @property
    def heartbeat_stale(self):
        return (self.status == self.Status.RUNNING and self.heartbeat_at is not None
                and (timezone.now() - self.heartbeat_at).total_seconds() > 30)


class CeleryTestTask(models.Model):
    class Status(models.TextChoices):
        QUEUED = 'queued', 'Queued'
        RUNNING = 'running', 'Running'
        RETRYING = 'retrying', 'Retrying'
        SUCCEEDED = 'succeeded', 'Succeeded'
        FAILED = 'failed', 'Failed'
        CANCELLED = 'cancelled', 'Cancelled'

    TERMINAL_STATUSES = (Status.SUCCEEDED, Status.FAILED, Status.CANCELLED)
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    suite = models.ForeignKey(CeleryTestSuite, related_name='tasks', on_delete=models.CASCADE)
    workload_index = models.PositiveSmallIntegerField(null=True, blank=True)
    scenario = models.CharField(max_length=100, blank=True)
    expected = models.JSONField(default=dict)
    observations = models.JSONField(default=dict)
    queue = models.CharField(max_length=255)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.QUEUED)
    submitted_at = models.DateTimeField(default=timezone.now)
    published_at = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    worker = models.CharField(max_length=255, blank=True)
    wait_seconds = models.FloatField(null=True, blank=True)
    runtime_seconds = models.FloatField(null=True, blank=True)
    total_seconds = models.FloatField(null=True, blank=True)
    error = models.TextField(blank=True)

    @property
    def scenario_name(self):
        return self.scenario.partition('.')[0]

    class Meta:
        indexes = [models.Index(fields=['suite', 'status'], name='celery_test_suite_status_idx')]


class CeleryTestTaskAttempt(models.Model):
    task = models.ForeignKey(CeleryTestTask, related_name='attempts', on_delete=models.CASCADE)
    number = models.PositiveSmallIntegerField()
    started_at = models.DateTimeField(default=timezone.now)
    finished_at = models.DateTimeField(null=True, blank=True)
    retry_at = models.DateTimeField(null=True, blank=True)
    worker = models.CharField(max_length=255, blank=True)
    outcome = models.CharField(max_length=32, blank=True)
    error = models.TextField(blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['task', 'number'], name='celery_test_attempt_unique')]

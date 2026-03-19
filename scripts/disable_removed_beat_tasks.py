from framework.celery_tasks import app as celery_app
from website import settings
from django.db.models import Q
from django_celery_beat.models import PeriodicTask, PeriodicTasks


@celery_app.task(name='scripts.disable_removed_beat_tasks')
def disable_removed_beat_tasks():
    """
    Disable django-celery-beat PeriodicTask entries that no longer exist
    and re-enable those that do exist, based on the current CeleryConfig.beat_schedule.
    """

    beat_schedule_keys = settings.CeleryConfig.beat_schedule.keys() if hasattr(settings.CeleryConfig, 'beat_schedule') else None
    if not beat_schedule_keys:
        return

    desired_task_names = set(beat_schedule_keys) | {'celery.backend_cleanup'} # Built-in backend cleanup task

    qs_disable = PeriodicTask.objects.filter(~Q(name__in=desired_task_names))
    qs_disable.update(enabled=False)
    qs_enable = PeriodicTask.objects.filter(name__in=desired_task_names)
    qs_enable.update(enabled=True)
    PeriodicTasks.update_changed()  # Notify django-celery-beat of the changes

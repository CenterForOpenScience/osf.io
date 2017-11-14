from django.dispatch import receiver
from django.db.models.signals import post_save

from api.caching.tasks import ban_url
from framework.postcommit_tasks.handlers import enqueue_postcommit_task


@receiver(post_save)
def ban_object_from_cache(sender, instance, created, **kwargs):
    if hasattr(instance, 'absolute_api_v2_url'):
        enqueue_postcommit_task(ban_url, (instance, ), {}, celery=False, once_per_request=True)

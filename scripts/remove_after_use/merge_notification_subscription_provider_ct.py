import django
django.setup()

from website.app import init_app
init_app(routes=False)

from django.contrib.contenttypes.models import ContentType
from framework.celery_tasks import app as celery_app
from osf.models import NotificationSubscription
from django.db.models import Exists, OuterRef
from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)



@celery_app.task(name='scripts.remove_after_use.merge_notification_subscription_provider_ct')
def merge_notification_subscription_provider_ct():

    abstract_provider_ct = ContentType.objects.get_by_natural_key('osf', 'abstractprovider')

    provider_ct_list = [
        ContentType.objects.get_by_natural_key('osf', 'preprintprovider'),
        ContentType.objects.get_by_natural_key('osf', 'registrationprovider'),
        ContentType.objects.get_by_natural_key('osf', 'collectionprovider'),
    ]

    provider_ct_ids = [ct.id for ct in provider_ct_list]

    abstract_qs = NotificationSubscription.objects.filter(
        content_type=abstract_provider_ct
    )

    duplicates = NotificationSubscription.objects.filter(
        content_type_id__in=provider_ct_ids
    ).annotate(
        abstract_exists=Exists(
            abstract_qs.filter(
                notification_type_id=OuterRef('notification_type_id'),
                user_id=OuterRef('user_id'),
                object_id=OuterRef('object_id'),
                _is_digest=OuterRef('_is_digest'),
            )
        )
    ).filter(abstract_exists=True)

    # delete rows that would conflict
    logger.info(f'Deleted {duplicates.count()} duplicate NotificationSubscription rows with provider content types.')
    duplicates.delete()

    # update remaining rows
    update_qs = NotificationSubscription.objects.filter(
        content_type_id__in=provider_ct_ids
    )
    logger.info(f'Updated {update_qs.count()} NotificationSubscription rows to use abstract provider content type.')
    update_qs.update(content_type=abstract_provider_ct)


if __name__ == '__main__':
    merge_notification_subscription_provider_ct.delay()

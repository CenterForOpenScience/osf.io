import django
django.setup()

from website.app import init_app
init_app(routes=False)

from django.contrib.contenttypes.models import ContentType
from framework.celery_tasks import app as celery_app
from osf.models import NotificationSubscription


@celery_app.task(name='scripts.remove_after_use.notification_subscription_provider_ct')
def update_notification_subscription_provider_ct():

    abstract_provider_ct = ContentType.objects.get_by_natural_key('osf', 'abstractprovider')

    provider_ct_list = [
        ContentType.objects.get_by_natural_key('osf', 'preprintprovider'),
        ContentType.objects.get_by_natural_key('osf', 'registrationprovider'),
        ContentType.objects.get_by_natural_key('osf', 'collectionprovider'),
    ]
    subscriptions = NotificationSubscription.objects.filter(
        content_type__in=provider_ct_list
    )
    subscriptions.update(
        content_type=abstract_provider_ct
    )


if __name__ == '__main__':
    update_notification_subscription_provider_ct.delay()
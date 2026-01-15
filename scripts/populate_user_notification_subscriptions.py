import django
django.setup()

from website.app import init_app
init_app(routes=False)

from framework.celery_tasks import app as celery_app
from django.contrib.contenttypes.models import ContentType
from osf.models import OSFUser,  NotificationSubscription, NotificationType


@celery_app.task(name='scripts.populate_user_notification_subscriptions')
def populate_user_notification_subscriptions():
    created = 0
    user_file_nt = NotificationType.Type.USER_FILE_UPDATED.instance

    user_ct = ContentType.objects.get_for_model(OSFUser)

    files_qs = OSFUser.objects.exclude(subscriptions__notification_type__name=NotificationType.Type.USER_FILE_UPDATED).distinct('id')

    print(f"Creating USER_FILE_UPDATED subscriptions for {files_qs.count()} users.")
    for id, user in enumerate(files_qs, 1):
        print(f"Processing user {id} / {files_qs.count()}")
        try:
            _, is_created = NotificationSubscription.objects.get_or_create(
                notification_type=user_file_nt,
                user=user,
                content_type=user_ct,
                object_id=user.id,
                defaults={
                    '_is_digest': True,
                    'message_frequency': 'none',
                },
            )
            if is_created:
                created += 1
        except Exception as exeption:
            print(exeption)
            continue

    print(f"Created {created} subscriptions")

if __name__ == '__main__':
    populate_user_notification_subscriptions.delay()

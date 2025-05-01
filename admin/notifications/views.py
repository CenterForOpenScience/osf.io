from osf.models.notification import NotificationSubscription
from django.db.models import Count

def delete_selected_notifications(selected_ids):
    NotificationSubscription.objects.filter(id__in=selected_ids).delete()

def detect_duplicate_notifications(node_id=None):
    query = NotificationSubscription.objects.annotate(count=Count('id')).filter(count__gt=1)
    if node_id:
        query = query.filter(node_id=node_id)

    detailed_duplicates = []
    for dup in query:
        notifications = NotificationSubscription.objects.filter(
            _id=dup['_id']
        ).order_by('created')

        for notification in notifications:
            detailed_duplicates.append({
                'id': notification.id,
                '_id': notification._id,
                'event_name': notification.event_name,
                'created': notification.created,
                'count': dup['count'],
                'email_transactional': [u._id for u in notification.email_transactional.all()],
                'email_digest': [u._id for u in notification.email_digest.all()],
                'none': [u._id for u in notification.none.all()]
            })

    return detailed_duplicates

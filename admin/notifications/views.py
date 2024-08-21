from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import render, redirect
from django.urls import reverse
from admin.base.utils import osf_staff_check
from osf.models.notifications import NotificationSubscription
from django.db.models import Count

def delete_selected_notifications(selected_ids):
    NotificationSubscription.objects.filter(id__in=selected_ids).delete()

def detect_duplicate_notifications(node_id=None):
    query = NotificationSubscription.objects.values('_id').annotate(count=Count('_id')).filter(count__gt=1)
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


def process_duplicate_notifications(request, node_id=None):
    detailed_duplicates = detect_duplicate_notifications(node_id)

    if request.method == 'POST':
        selected_ids = request.POST.getlist('selected_notifications')
        delete_selected_notifications(selected_ids)
        return detailed_duplicates, 'Selected duplicate notifications have been deleted.', True

    return detailed_duplicates, '', False

@user_passes_test(osf_staff_check)
def handle_duplicate_notifications(request):
    node_id = request.GET.get('node_id')
    detailed_duplicates, message, is_post = process_duplicate_notifications(request, node_id)

    context = {'duplicates': detailed_duplicates, 'node_id': node_id}
    if is_post:
        context['message'] = message
        return redirect(f"{reverse('notifications:handle_duplicate_notifications')}?node_id={node_id}")

    return render(request, 'notifications/handle_duplicate_notifications.html', context)

from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import render, redirect
from admin.base.utils import osf_staff_check
from osf.models.notifications import NotificationSubscription
from django.db.models import Count

def delete_selected_notifications(selected_ids):
    NotificationSubscription.objects.filter(id__in=selected_ids).delete()

def detect_duplicate_notifications():
    duplicates = (
        NotificationSubscription.objects.values('user', 'node', 'event_name')
        .annotate(count=Count('id'))
        .filter(count__gt=1)
    )

    detailed_duplicates = []
    for dup in duplicates:
        notifications = NotificationSubscription.objects.filter(
            user=dup['user'], node=dup['node'], event_name=dup['event_name']
        ).order_by('created')

        for notification in notifications:
            detailed_duplicates.append({
                'id': notification.id,
                'user': notification.user,
                'node': notification.node,
                'event_name': notification.event_name,
                'created': notification.created,
                'count': dup['count']
            })

    return detailed_duplicates

def process_duplicate_notifications(request):
    detailed_duplicates = detect_duplicate_notifications()

    if request.method == 'POST':
        selected_ids = request.POST.getlist('selected_notifications')
        delete_selected_notifications(selected_ids)
        return detailed_duplicates, 'Selected duplicate notifications have been deleted.', True

    return detailed_duplicates, '', False

@user_passes_test(osf_staff_check)
def handle_duplicate_notifications(request):
    detailed_duplicates, message, is_post = process_duplicate_notifications(request)

    context = {'duplicates': detailed_duplicates}
    if is_post:
        context['message'] = message
        return redirect('notifications:handle_duplicate_notifications')

    return render(request, 'notifications/handle_duplicate_notifications.html', context)

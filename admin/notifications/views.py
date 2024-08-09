from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import render, redirect
from admin.base.utils import osf_staff_check
from osf.models.notifications import NotificationSubscription
from django.db.models import Count

@user_passes_test(osf_staff_check)
def handle_duplicate_notifications(request):
    duplicates = NotificationSubscription.objects.values('user', 'node', 'event_name').annotate(count=Count('id')).filter(count__gt=1)

    detailed_duplicates = []
    for dup in duplicates:
        notifications = NotificationSubscription.objects.filter(user=dup['user'], node=dup['node'], event_name=dup['event_name'])
        for notification in notifications:
            detailed_duplicates.append({
                'id': notification.id,
                'user': notification.user,
                'node': notification.node,
                'event_name': notification.event_name,
                'created': notification.created,
                'count': dup['count']
            })

    context = {'duplicates': detailed_duplicates}

    if request.method == 'POST':
        selected_ids = request.POST.getlist('selected_notifications')
        NotificationSubscription.objects.filter(id__in=selected_ids).delete()
        context['message'] = 'Selected duplicate notifications have been deleted.'
        return redirect('notifications:handle_duplicate_notifications')

    return render(request, 'handle_duplicate_notifications.html', context)
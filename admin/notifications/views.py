from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import render, redirect
from django.core.paginator import Paginator
from admin.base.utils import osf_staff_check
from osf.models.notifications import NotificationSubscription
from django.db.models import Count

def delete_selected_notifications(selected_ids):
    NotificationSubscription.objects.filter(id__in=selected_ids).delete()

def detect_duplicate_notifications():
    duplicates = (
        NotificationSubscription.objects.values('_id')
        .annotate(count=Count('_id'))
        .filter(count__gt=1)
    )

    detailed_duplicates = []
    for dup in duplicates:
        notifications = NotificationSubscription.objects.filter(
            _id=dup['_id']
        ).order_by('created')

        if notifications.exists():
            notification = notifications.first()
            detailed_duplicates.append({
                'id': notification.id,
                '_id': notification._id,
                'event_name': notification.event_name,
                'created': notification.created,
                'count': dup['count'],
                'email_transactional': [u._id for u in notification.email_transactional.all()],
                'email_digest': [u._id for u in notification.email_digest.all()]
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

    paginator = Paginator(detailed_duplicates, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {'duplicates': page_obj}
    if is_post:
        context['message'] = message
        return redirect('notifications:handle_duplicate_notifications')

    return render(request, 'notifications/handle_duplicate_notifications.html', context)

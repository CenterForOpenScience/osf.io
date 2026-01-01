from osf.models.notification_subscription import NotificationSubscription

def delete_selected_notifications(selected_ids):
    NotificationSubscription.objects.filter(id__in=selected_ids).delete()

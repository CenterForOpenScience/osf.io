from rest_framework import permissions

from osf.models.notifications import NotificationSubscription


class IsSubscriptionOwner(permissions.BasePermission):

    def has_object_permission(self, request, view, obj):
        assert isinstance(obj, NotificationSubscription), 'obj must be a NotificationSubscription; got {}'.format(obj)
        user_id = request.user.id
        return obj.none.filter(id=user_id).exists() \
               or obj.email_transactional.filter(id=user_id).exists() \
               or obj.email_digest.filter(id=user_id).exists()

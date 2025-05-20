from rest_framework import permissions

from osf.models.notifications import NotificationSubscriptionLegacy


class IsSubscriptionOwner(permissions.BasePermission):

    def has_object_permission(self, request, view, obj):
        assert isinstance(obj, NotificationSubscriptionLegacy), f'obj must be a NotificationSubscriptionLegacy; got {obj}'
        user_id = request.user.id
        return obj.none.filter(id=user_id).exists() \
               or obj.email_transactional.filter(id=user_id).exists() \
               or obj.email_digest.filter(id=user_id).exists()

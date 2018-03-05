from rest_framework import permissions

from osf.models.notifications import NotificationSubscription


class IsOwner(permissions.BasePermission):

    def has_object_permission(self, request, view, obj):
        assert isinstance(obj, NotificationSubscription), 'obj must be an NotificationSubscription; got {}'.format(obj)
        user = request.user
        is_owner = False
        if obj.user is user:
            is_owner = True
        elif user in obj.none.all() or user in obj.email_transactional.all() or user in obj.email_digest.all():
            is_owner = True
        return is_owner

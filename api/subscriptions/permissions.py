from rest_framework import permissions
from osf.models import NotificationSubscription

class IsSubscriptionOwner(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        assert isinstance(obj, NotificationSubscription), f'obj must be NotificationSubscription; got {obj}'
        return obj.user == request.user

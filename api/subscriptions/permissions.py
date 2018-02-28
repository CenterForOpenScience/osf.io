from rest_framework import permissions

from api.base.utils import get_user_auth
from osf.models.notifications import NotificationSubscription
from osf.models.user import OSFUser


class IsSelf(permissions.BasePermission):

    def has_object_permission(self, request, view, obj):
        assert isinstance(obj, NotificationSubscription), 'obj must be an NotificationSubscription; got {}'.format(obj)
        user = OSFUser.load(view.kwargs['user_id'])
        auth = get_user_auth(request)
        if auth.user != user:
            return False
        else:
            return True

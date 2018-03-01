from rest_framework import generics
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework import permissions as drf_permissions

from api.base.views import JSONAPIBaseView
from api.subscriptions.serializers import UserProviderSubscriptionSerializer
from api.subscriptions.permissions import IsSelf
from osf.models import PreprintProvider, OSFUser


class UserProviderSubscriptionDetail(JSONAPIBaseView, generics.RetrieveUpdateAPIView):
    view_name = 'user-provider-subscription-detail'
    view_category = 'subscriptions'
    serializer_class = UserProviderSubscriptionSerializer
    permission_classes = (
        drf_permissions.IsAuthenticated,
        IsSelf
    )

    def get_object(self):
        provider_id = self.kwargs['provider_id']
        user_id = self.kwargs['user_id']
        current_user_id = self.request.user._id
        if user_id != current_user_id:
            raise PermissionDenied()
        user = OSFUser.load(user_id)
        if not user:
            raise NotFound('User with id {} cannot be found.'.format(user_id))
        provider = PreprintProvider.objects.get(_id=provider_id)
        notification = provider.notification_subscriptions.get(_id='{}_preprints_added'.format(provider._id))
        subscribers = notification.none.all() | notification.email_transactional.all() | notification.email_digest.all()
        if user not in subscribers:
            raise NotFound('User with id {} cannot be found in the list of subscribers.'.format(user_id))
        self.check_object_permissions(self.request, notification)
        return notification


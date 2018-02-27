from rest_framework import generics
from rest_framework.exceptions import NotFound

from api.base.views import JSONAPIBaseView
from api.subscriptions.serializers import UserProviderSubscriptionSerializer
from osf.models import NotificationSubscription, PreprintProvider, OSFUser


class UserProviderSubscriptionDetail(JSONAPIBaseView, generics.RetrieveUpdateAPIView):
    view_name = 'user-provider-subscription-detail'
    view_category = 'subscriptions'
    serializer_class = UserProviderSubscriptionSerializer

    def get_object(self):
        provider_id = self.kwargs['provider_id']
        user_id = self.kwargs['user_id']
        user = OSFUser.load(user_id)
        if not user:
            raise NotFound('User with id {} cannot be found.'.format(user_id))
        provider = PreprintProvider.objects.get(_id=provider_id)
        notification = NotificationSubscription.objects.get(provider=provider)
        subscribers = notification.none.all() | notification.email_transactional.all() | notification.email_digest.all()
        if user not in subscribers:
            raise NotFound('{} cannot be found in the list of subscribers.'.format(user))

        return notification


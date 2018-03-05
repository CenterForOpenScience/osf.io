from rest_framework import generics
from rest_framework import permissions as drf_permissions
from rest_framework.exceptions import PermissionDenied
from django.core.exceptions import ObjectDoesNotExist

from api.base.views import JSONAPIBaseView
from api.base.filters import ListFilterMixin
from api.subscriptions.serializers import UserProviderSubscriptionDetailSerializer, UserProviderSubscriptionListSerializer
from api.subscriptions.permissions import IsOwner
from osf.models import NotificationSubscription


class UserProviderSubscriptionList(JSONAPIBaseView, generics.ListAPIView, ListFilterMixin):
    view_name = 'user-provider-subscription-list'
    view_category = 'subscriptions'
    serializer_class = UserProviderSubscriptionListSerializer
    permission_classes = (
        drf_permissions.IsAuthenticated,
    )

    def get_queryset(self):
        user = self.request.user
        notification_none = NotificationSubscription.objects.filter(none=user)
        notification_daily = NotificationSubscription.objects.filter(email_digest=user)
        notification_instant = NotificationSubscription.objects.filter(email_transactional=user)
        return notification_none | notification_daily | notification_instant


class UserProviderSubscriptionDetail(JSONAPIBaseView, generics.RetrieveUpdateAPIView):
    view_name = 'user-provider-subscription-detail'
    view_category = 'subscriptions'
    serializer_class = UserProviderSubscriptionDetailSerializer
    permission_classes = (
        drf_permissions.IsAuthenticated,
        IsOwner
    )

    def get_object(self):
        subscription_id = self.kwargs['subscription_id']
        try:
            subscription = NotificationSubscription.objects.get(_id=subscription_id)
        except ObjectDoesNotExist:
            raise PermissionDenied
        return subscription

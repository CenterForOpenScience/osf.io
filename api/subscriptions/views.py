from rest_framework import generics
from rest_framework import permissions as drf_permissions
from rest_framework.exceptions import NotFound
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q

from api.base.views import JSONAPIBaseView
from api.base.filters import ListFilterMixin
from api.subscriptions.serializers import SubscriptionDetailSerializer, SubscriptionListSerializer
from api.subscriptions.permissions import IsSubscriptionOwner
from osf.models import NotificationSubscription


class SubscriptionList(JSONAPIBaseView, generics.ListAPIView, ListFilterMixin):
    view_name = 'user-provider-subscription-list'
    view_category = 'subscriptions'
    serializer_class = SubscriptionListSerializer
    permission_classes = (
        drf_permissions.IsAuthenticated,
    )

    def get_queryset(self):
        user = self.request.user
        queryset = NotificationSubscription.objects.filter(Q(none=user) | Q(email_digest=user) | Q(email_transactional=user))
        return queryset


class SubscriptionDetail(JSONAPIBaseView, generics.RetrieveUpdateAPIView):
    view_name = 'user-provider-subscription-detail'
    view_category = 'subscriptions'
    serializer_class = SubscriptionDetailSerializer
    permission_classes = (
        drf_permissions.IsAuthenticated,
        IsSubscriptionOwner
    )

    def get_object(self):
        subscription_id = self.kwargs['subscription_id']
        try:
            subscription = NotificationSubscription.objects.get(_id=subscription_id)
        except ObjectDoesNotExist:
            raise NotFound
        return subscription

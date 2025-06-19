from pyasn1_modules.rfc5126 import ContentType
from rest_framework import generics
from rest_framework import permissions as drf_permissions
from rest_framework.exceptions import NotFound
from django.core.exceptions import ObjectDoesNotExist

from framework.auth.oauth_scopes import CoreScopes
from api.base.views import JSONAPIBaseView
from api.base.filters import ListFilterMixin
from api.base import permissions as base_permissions
from api.subscriptions.serializers import (
    SubscriptionSerializer,
    CollectionSubscriptionSerializer,
    PreprintSubscriptionSerializer,
    RegistrationSubscriptionSerializer,
)
from api.subscriptions.permissions import IsSubscriptionOwner
from osf.models import (
    CollectionProvider,
    PreprintProvider,
    RegistrationProvider,
    AbstractProvider,
)
from osf.models.notification import NotificationSubscription


class SubscriptionList(JSONAPIBaseView, generics.ListAPIView, ListFilterMixin):
    view_name = 'notification-subscription-list'
    view_category = 'notification-subscriptions'
    serializer_class = SubscriptionSerializer
    model_class = NotificationSubscription
    permission_classes = (
        drf_permissions.IsAuthenticated,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.SUBSCRIPTIONS_READ]
    required_write_scopes = [CoreScopes.NULL]

    def get_queryset(self):
        return NotificationSubscription.objects.filter(
            user=self.request.user,
        )


class AbstractProviderSubscriptionList(SubscriptionList):
    def get_queryset(self):
        provider = AbstractProvider.objects.get(_id=self.kwargs['provider_id'])
        return NotificationSubscription.objects.filter(
            object_id=provider,
            provider__type=ContentType.objects.get_for_model(provider.__class__),
            user=self.request.user,
        )

class SubscriptionDetail(JSONAPIBaseView, generics.RetrieveUpdateAPIView):
    view_name = 'notification-subscription-detail'
    view_category = 'notification-subscriptions'
    serializer_class = SubscriptionSerializer
    permission_classes = (
        drf_permissions.IsAuthenticated,
        base_permissions.TokenHasScope,
        IsSubscriptionOwner,
    )

    required_read_scopes = [CoreScopes.SUBSCRIPTIONS_READ]
    required_write_scopes = [CoreScopes.SUBSCRIPTIONS_WRITE]

    def get_object(self):
        subscription_id = self.kwargs['subscription_id']
        try:
            obj = NotificationSubscription.objects.get(id=subscription_id)
        except ObjectDoesNotExist:
            raise NotFound
        self.check_object_permissions(self.request, obj)
        return obj


class AbstractProviderSubscriptionDetail(SubscriptionDetail):
    view_name = 'provider-notification-subscription-detail'
    view_category = 'notification-subscriptions'
    permission_classes = (
        drf_permissions.IsAuthenticated,
        base_permissions.TokenHasScope,
        IsSubscriptionOwner,
    )

    required_read_scopes = [CoreScopes.SUBSCRIPTIONS_READ]
    required_write_scopes = [CoreScopes.SUBSCRIPTIONS_WRITE]
    provider_class = None

class CollectionProviderSubscriptionDetail(AbstractProviderSubscriptionDetail):
    provider_class = CollectionProvider
    serializer_class = CollectionSubscriptionSerializer


class PreprintProviderSubscriptionDetail(AbstractProviderSubscriptionDetail):
    provider_class = PreprintProvider
    serializer_class = PreprintSubscriptionSerializer


class RegistrationProviderSubscriptionDetail(AbstractProviderSubscriptionDetail):
    provider_class = RegistrationProvider
    serializer_class = RegistrationSubscriptionSerializer


class CollectionProviderSubscriptionList(AbstractProviderSubscriptionList):
    provider_class = CollectionProvider
    serializer_class = CollectionSubscriptionSerializer


class PreprintProviderSubscriptionList(AbstractProviderSubscriptionList):
    provider_class = PreprintProvider
    serializer_class = PreprintSubscriptionSerializer


class RegistrationProviderSubscriptionList(AbstractProviderSubscriptionList):
    provider_class = RegistrationProvider
    serializer_class = RegistrationSubscriptionSerializer

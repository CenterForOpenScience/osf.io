from api.base.filters import ListFilterMixin
from api.subscriptions.serializers import SubscriptionSerializer
from osf.models.notification import NotificationSubscription
from django.contrib.contenttypes.models import ContentType
from rest_framework import generics, permissions as drf_permissions
from rest_framework.exceptions import NotFound
from django.shortcuts import get_object_or_404

from osf.models import AbstractProvider, CollectionProvider, PreprintProvider, RegistrationProvider

from api.base.views import JSONAPIBaseView
from api.base import permissions as base_permissions
from api.subscriptions.permissions import IsSubscriptionOwner
from api.subscriptions.serializers import (
    CollectionSubscriptionSerializer,
    PreprintSubscriptionSerializer,
    RegistrationSubscriptionSerializer,
)
from framework.auth.oauth_scopes import CoreScopes

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
        return NotificationSubscription.objects.filter(user=self.request.user)

class AbstractProviderSubscriptionList(SubscriptionList):
    permission_classes = (
        drf_permissions.IsAuthenticated,
        base_permissions.TokenHasScope,
    )
    required_read_scopes = [CoreScopes.SUBSCRIPTIONS_READ]
    provider_class = None
    serializer_class = None

    def get_queryset(self):
        assert issubclass(self.provider_class, AbstractProvider), 'Must set provider_class to an AbstractProvider subclass'
        provider_id = self.kwargs.get('provider_id')
        provider = get_object_or_404(self.provider_class, _id=provider_id)

        return NotificationSubscription.objects.filter(
            user=self.request.user,
            content_type=ContentType.objects.get_for_model(self.provider_class),
            object_id=provider.id,
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
        try:
            sub = NotificationSubscription.objects.get(pk=self.kwargs['pk'])
        except NotificationSubscription.DoesNotExist:
            raise NotFound
        self.check_object_permissions(self.request, sub)
        return sub


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

    def __init__(self, *args, **kwargs):
        assert issubclass(self.provider_class, AbstractProvider), 'Class must be subclass of AbstractProvider'
        super().__init__(*args, **kwargs)

    def get_object(self):
        assert issubclass(self.provider_class, AbstractProvider), 'Must set provider_class to an AbstractProvider subclass'

        subscription_id = self.kwargs.get('pk')
        provider_id = self.kwargs.get('provider_id')

        # Get provider
        provider = get_object_or_404(self.provider_class, _id=provider_id)
        content_type = ContentType.objects.get_for_model(self.provider_class)

        try:
            sub = NotificationSubscription.objects.get(
                pk=subscription_id,
                content_type=content_type,
                object_id=provider.id,
            )
        except NotificationSubscription.DoesNotExist:
            raise NotFound

        self.check_object_permissions(self.request, sub)
        return sub


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

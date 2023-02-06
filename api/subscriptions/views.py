from rest_framework import generics
from rest_framework import permissions as drf_permissions
from rest_framework.exceptions import NotFound
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q

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
    NotificationSubscription,
    CollectionProvider,
    PreprintProvider,
    RegistrationProvider,
    AbstractProvider,
)


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

    def get_default_queryset(self):
        user = self.request.user
        return NotificationSubscription.objects.filter(
            Q(none=user) |
            Q(email_digest=user) |
            Q(
                email_transactional=user,
            ),
        ).distinct()

    def get_queryset(self):
        return self.get_queryset_from_request()


class AbstractProviderSubscriptionList(SubscriptionList):
    def get_default_queryset(self):
        user = self.request.user
        return NotificationSubscription.objects.filter(
            provider___id=self.kwargs['provider_id'],
            provider__type=self.provider_class._typedmodels_type,
        ).filter(
            Q(none=user) |
            Q(email_digest=user) |
            Q(email_transactional=user),
        ).distinct()


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
            obj = NotificationSubscription.objects.get(_id=subscription_id)
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

    def __init__(self, *args, **kwargs):
        assert issubclass(self.provider_class, AbstractProvider), 'Class must be subclass of AbstractProvider'
        super().__init__(*args, **kwargs)

    def get_object(self):
        subscription_id = self.kwargs['subscription_id']
        if self.kwargs.get('provider_id'):
            provider = self.provider_class.objects.get(_id=self.kwargs.get('provider_id'))
            try:
                obj = NotificationSubscription.objects.get(
                    _id=subscription_id,
                    provider_id=provider.id,
                )
            except ObjectDoesNotExist:
                raise NotFound
        else:
            try:
                obj = NotificationSubscription.objects.get(
                    _id=subscription_id,
                    provider__type=self.provider_class._typedmodels_type,
                )
            except ObjectDoesNotExist:
                    raise NotFound
        self.check_object_permissions(self.request, obj)
        return obj


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

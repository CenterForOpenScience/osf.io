from django.db.models import Value, When, Case, F, Q, OuterRef, Subquery
from django.db.models.fields import CharField, IntegerField
from django.db.models.functions import Concat, Cast
from django.contrib.contenttypes.models import ContentType
from rest_framework import generics
from rest_framework import permissions as drf_permissions
from rest_framework.exceptions import NotFound
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied

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
    AbstractNode,
    Preprint,
    OSFUser,
)
from osf.models.notification_type import NotificationType
from osf.models.notification_subscription import NotificationSubscription


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
        user_guid = self.request.user._id
        provider_ct = ContentType.objects.get(app_label='osf', model='abstractprovider')

        provider_subquery = AbstractProvider.objects.filter(
            id=Cast(OuterRef('object_id'), IntegerField()),
        ).values('_id')[:1]

        node_subquery = AbstractNode.objects.filter(
            id=Cast(OuterRef('object_id'), IntegerField()),
        ).values('guids___id')[:1]

        return NotificationSubscription.objects.filter(user=self.request.user).annotate(
            event_name=Case(
                When(
                    notification_type__name=NotificationType.Type.NODE_FILES_UPDATED.value,
                    then=Value('files_updated'),
                ),
                When(
                    notification_type__name=NotificationType.Type.USER_FILE_UPDATED.value,
                    then=Value('global_file_updated'),
                ),
                default=F('notification_type__name'),
                output_field=CharField(),
            ),
            legacy_id=Case(
                When(
                    notification_type__name=NotificationType.Type.NODE_FILES_UPDATED.value,
                    then=Concat(Subquery(node_subquery), Value('_file_updated')),
                ),
                When(
                    notification_type__name=NotificationType.Type.USER_FILE_UPDATED.value,
                    then=Value(f'{user_guid}_global'),
                ),
                When(
                    Q(notification_type__name=NotificationType.Type.PROVIDER_NEW_PENDING_SUBMISSIONS.value) &
                    Q(content_type=provider_ct),
                    then=Concat(Subquery(provider_subquery), Value('_new_pending_submissions')),
                ),
                default=F('notification_type__name'),
                output_field=CharField(),
            ),
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
        user_guid = self.request.user._id

        provider_ct = ContentType.objects.get(app_label='osf', model='abstractprovider')
        node_ct = ContentType.objects.get(app_label='osf', model='abstractnode')

        provider_subquery = AbstractProvider.objects.filter(
            id=Cast(OuterRef('object_id'), IntegerField()),
        ).values('_id')[:1]

        node_subquery = AbstractNode.objects.filter(
            id=Cast(OuterRef('object_id'), IntegerField()),
        ).values('guids___id')[:1]

        guid_id, *event_parts = subscription_id.split('_')
        event = '_'.join(event_parts) if event_parts else ''

        subscription_obj = AbstractNode.load(guid_id) or Preprint.load(guid_id) or OSFUser.load(guid_id)

        if event != 'global':
            obj_filter = Q(
                object_id=getattr(subscription_obj, 'id', None),
                content_type=ContentType.objects.get_for_model(subscription_obj.__class__),
                notification_type__name__icontains=event,
            )
        else:
            obj_filter = Q()

        try:
            obj = NotificationSubscription.objects.annotate(
                legacy_id=Case(
                    When(
                        notification_type__name=NotificationType.Type.NODE_FILES_UPDATED.value,
                        content_type=node_ct,
                        then=Concat(Subquery(node_subquery), Value('_file_updated')),
                    ),
                    When(
                        notification_type__name=NotificationType.Type.USER_FILE_UPDATED.value,
                        then=Value(f'{user_guid}_global'),
                    ),
                    When(
                        notification_type__name=NotificationType.Type.PROVIDER_NEW_PENDING_SUBMISSIONS.value,
                        content_type=provider_ct,
                        then=Concat(Subquery(provider_subquery), Value('_new_pending_submissions')),
                    ),
                    default=Value(f'{user_guid}_global'),
                    output_field=CharField(),
                ),
            ).filter(obj_filter)

        except ObjectDoesNotExist:
            raise NotFound

        try:
            obj = obj.filter(user=self.request.user).get()
        except ObjectDoesNotExist:
            raise PermissionDenied

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

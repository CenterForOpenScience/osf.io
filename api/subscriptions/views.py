from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied
from django.db.models import Value, When, Case, OuterRef, Subquery, F
from django.db.models.fields import CharField, IntegerField
from django.db.models.functions import Concat, Cast

from rest_framework import generics
from rest_framework import permissions as drf_permissions
from rest_framework.response import Response

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
from api.subscriptions import utils

from osf.models import (
    CollectionProvider,
    PreprintProvider,
    RegistrationProvider,
    AbstractProvider,
    AbstractNode,
    Guid,
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

        user = self.request.user
        user_guid = self.request.user._id

        filter_id = self.request.query_params.get('filter[id]')
        filter_event_name = self.request.query_params.get('filter[event_name]')

        provider_ct = ContentType.objects.get_for_model(AbstractProvider)
        node_ct = ContentType.objects.get_for_model(AbstractNode)
        user_ct = ContentType.objects.get_for_model(OSFUser)

        node_subquery = AbstractNode.objects.filter(
            id=Cast(OuterRef('object_id'), IntegerField()),
        ).values('guids___id')[:1]

        _global_file_updated = [
            NotificationType.Type.USER_FILE_UPDATED.value,
            NotificationType.Type.FILE_ADDED.value,
            NotificationType.Type.FILE_REMOVED.value,
            NotificationType.Type.ADDON_FILE_COPIED.value,
            NotificationType.Type.ADDON_FILE_RENAMED.value,
            NotificationType.Type.ADDON_FILE_MOVED.value,
            NotificationType.Type.ADDON_FILE_REMOVED.value,
            NotificationType.Type.FOLDER_CREATED.value,
        ]
        _global_reviews_provider = [
            NotificationType.Type.PROVIDER_NEW_PENDING_SUBMISSIONS.value,
            NotificationType.Type.PROVIDER_REVIEWS_SUBMISSION_CONFIRMATION.value,
            NotificationType.Type.PROVIDER_REVIEWS_RESUBMISSION_CONFIRMATION.value,
            NotificationType.Type.PROVIDER_NEW_PENDING_WITHDRAW_REQUESTS.value,
        ]
        _global_reviews_user = [
            NotificationType.Type.REVIEWS_SUBMISSION_STATUS.value,
        ]
        _node_file_updated = [
            NotificationType.Type.NODE_FILE_UPDATED.value,
            NotificationType.Type.FILE_ADDED.value,
            NotificationType.Type.FILE_REMOVED.value,
            NotificationType.Type.ADDON_FILE_COPIED.value,
            NotificationType.Type.ADDON_FILE_RENAMED.value,
            NotificationType.Type.ADDON_FILE_MOVED.value,
            NotificationType.Type.ADDON_FILE_REMOVED.value,
            NotificationType.Type.FOLDER_CREATED.value,
            NotificationType.Type.FILE_UPDATED.value,
        ]

        full_set_of_types = _global_reviews_provider + _global_reviews_user + _global_file_updated + _node_file_updated
        annotated_qs = NotificationSubscription.objects.filter(
            notification_type__name__in=full_set_of_types,
            user=user,
        ).annotate(
            event_name=Case(
                When(
                    notification_type__name__in=_node_file_updated,
                    content_type=node_ct,
                    then=Value('file_updated'),
                ),
                When(
                    notification_type__name__in=_global_file_updated,
                    content_type=user_ct,
                    then=Value('global_file_updated'),
                ),
                When(
                    notification_type__name__in=_global_reviews_provider,
                    content_type=provider_ct,
                    then=Value('global_reviews'),
                ),
                When(
                    notification_type__name__in=_global_reviews_user,
                    content_type=user_ct,
                    then=Value('global_reviews'),
                ),
                default=F('notification_type__name'),
            ),
            legacy_id=Case(
                When(
                    notification_type__name__in=_node_file_updated,
                    then=Concat(Subquery(node_subquery), Value('_file_updated')),
                ),
                When(
                    notification_type__name__in=_global_file_updated,
                    then=Value(f'{user_guid}_global_file_updated'),
                ),
                When(
                    notification_type__name__in=_global_reviews_provider,
                    content_type=provider_ct,
                    then=Value(f'{user_guid}_global_reviews'),
                ),
                When(
                    notification_type__name__in=_global_reviews_user,
                    content_type=user_ct,
                    then=Value(f'{user_guid}_global_reviews'),
                ),
                default=F('notification_type__name'),
            ),
        ).distinct('legacy_id')

        return_qs = annotated_qs

        # Apply manual filter for legacy_id if requested
        if filter_id:
            return_qs = annotated_qs.filter(legacy_id=filter_id)
            # TODO: Rework missing subscription fix after fully populating the OSF DB with all missing notifications
            # NOTE: `.exists()` errors for unknown reason, possibly due to complex annotation with `.distinct()`
            if return_qs.count() == 0:
                missing_subscription_created = utils.create_missing_notification_from_legacy_id(filter_id, user)
                if missing_subscription_created:
                    return_qs = annotated_qs.filter(legacy_id=filter_id)
            # `filter_id` takes priority over `filter_event_name`
            return return_qs

        # Apply manual filter for event_name if requested
        if filter_event_name:
            filter_event_names = filter_event_name.split(',')
            return_qs = annotated_qs.filter(event_name__in=filter_event_names)
            # TODO: Rework missing subscription fix after fully populating the OSF DB with all missing notifications
            # NOTE: `.exists()` errors for unknown reason, possibly due to complex annotation with `.distinct()`
            if return_qs.count() == 0:
                utils.create_missing_notifications_from_event_name(filter_event_names, user)

        return return_qs


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
        user = self.request.user
        user_guid = self.request.user._id
        user_ct = ContentType.objects.get_for_model(OSFUser)
        node_ct = ContentType.objects.get_for_model(AbstractNode)

        node_subquery = AbstractNode.objects.filter(
            id=Cast(OuterRef('object_id'), IntegerField()),
        ).values('guids___id')[:1]

        missing_subscription_created = None
        annotated_obj_qs = NotificationSubscription.objects.filter(user=user).annotate(
            legacy_id=Case(
                When(
                    notification_type__name=NotificationType.Type.NODE_FILE_UPDATED.value,
                    content_type=node_ct,
                    then=Concat(Subquery(node_subquery), Value('_file_updated')),
                ),
                When(
                    notification_type__name=NotificationType.Type.USER_FILE_UPDATED.value,
                    then=Value(f'{user_guid}_global_file_updated'),
                ),
                When(
                    notification_type__name=NotificationType.Type.REVIEWS_SUBMISSION_STATUS.value,
                    content_type=user_ct,
                    then=Value(f'{user_guid}_global_reviews'),
                ),
                default=Value(f'{user_guid}_global'),
                output_field=CharField(),
            ),
        )
        existing_subscriptions = annotated_obj_qs.filter(legacy_id=subscription_id)

        # TODO: Rework missing subscription fix after fully populating the OSF DB with all missing notifications
        if not existing_subscriptions.exists():
            missing_subscription_created = utils.create_missing_notification_from_legacy_id(subscription_id, user)
        if missing_subscription_created:
            # Note: must use `annotated_obj_qs` to insert `legacy_id` so that `SubscriptionSerializer` can build data
            # properly; in addition, there should be only one result
            # missing_subscription_created.legacy_id = subscription_id
            # subscription = missing_subscription_created
            subscription = annotated_obj_qs.get(legacy_id=subscription_id)
        else:
            # TODO: Use `get()` and fails/warns on multiple objects after fully de-duplicating the OSF DB
            subscription = existing_subscriptions.order_by('id').last()
        if not subscription:
            raise PermissionDenied

        self.check_object_permissions(self.request, subscription)
        return subscription

    def update(self, request, *args, **kwargs):
        """
        Update a notification subscription
        """
        self.get_object()

        if '_global_file_updated' in self.kwargs['subscription_id']:
            # Copy _global_file_updated subscription changes to all file subscriptions
            qs = NotificationSubscription.objects.filter(
                user=self.request.user,
                notification_type__name__in=[
                    NotificationType.Type.USER_FILE_UPDATED.value,
                    NotificationType.Type.FILE_UPDATED.value,
                    NotificationType.Type.FILE_ADDED.value,
                    NotificationType.Type.FILE_REMOVED.value,
                    NotificationType.Type.ADDON_FILE_COPIED.value,
                    NotificationType.Type.ADDON_FILE_RENAMED.value,
                    NotificationType.Type.ADDON_FILE_MOVED.value,
                    NotificationType.Type.ADDON_FILE_REMOVED.value,
                    NotificationType.Type.FOLDER_CREATED.value,
                ],
            ).exclude(content_type=ContentType.objects.get_for_model(AbstractNode))
            if not qs.exists():
                raise PermissionDenied

            for instance in qs:
                serializer = self.get_serializer(instance=instance, data=request.data, partial=True)
                serializer.is_valid(raise_exception=True)
                self.perform_update(serializer)
            return Response(serializer.data)
        elif '_global_reviews' in self.kwargs['subscription_id']:
            # Copy global_reviews subscription changes to all provider subscriptions [ENG-9666]
            qs = NotificationSubscription.objects.filter(
                user=self.request.user,
                notification_type__name__in=[
                    NotificationType.Type.PROVIDER_NEW_PENDING_SUBMISSIONS.value,
                    NotificationType.Type.PROVIDER_REVIEWS_SUBMISSION_CONFIRMATION.value,
                    NotificationType.Type.PROVIDER_REVIEWS_RESUBMISSION_CONFIRMATION.value,
                    NotificationType.Type.PROVIDER_NEW_PENDING_WITHDRAW_REQUESTS.value,
                    NotificationType.Type.REVIEWS_SUBMISSION_STATUS.value,
                ],
            )
            if not qs.exists():
                raise PermissionDenied

            for instance in qs:
                serializer = self.get_serializer(instance=instance, data=request.data, partial=True)
                serializer.is_valid(raise_exception=True)
                self.perform_update(serializer)
            return Response(serializer.data)
        elif '_file_updated' in self.kwargs['subscription_id']:
            # Copy _file_updated subscription changes to all node file subscriptions
            node_id = Guid.load(self.kwargs['subscription_id'].split('_file_updated')[0]).object_id

            qs = NotificationSubscription.objects.filter(
                user=self.request.user,
                content_type=ContentType.objects.get_for_model(AbstractNode),
                object_id=node_id,
                notification_type__name__in=[
                    NotificationType.Type.NODE_FILE_UPDATED.value,
                    NotificationType.Type.FILE_UPDATED.value,
                    NotificationType.Type.FILE_ADDED.value,
                    NotificationType.Type.FILE_REMOVED.value,
                    NotificationType.Type.ADDON_FILE_COPIED.value,
                    NotificationType.Type.ADDON_FILE_RENAMED.value,
                    NotificationType.Type.ADDON_FILE_MOVED.value,
                    NotificationType.Type.ADDON_FILE_REMOVED.value,
                    NotificationType.Type.FOLDER_CREATED.value,
                ],
            )
            if not qs.exists():
                raise PermissionDenied

            for instance in qs:
                serializer = self.get_serializer(instance=instance, data=request.data, partial=True)
                serializer.is_valid(raise_exception=True)
                self.perform_update(serializer)
            return Response(serializer.data)

        else:
            return super().update(request, *args, **kwargs)


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

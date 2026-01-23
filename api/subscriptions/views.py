from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied
from django.db.models import Value, When, Case, OuterRef, Subquery
from django.db.models.fields import CharField, IntegerField
from django.db.models.functions import Concat, Cast

from rest_framework import generics
from rest_framework import permissions as drf_permissions
from rest_framework.exceptions import NotFound
from rest_framework.response import Response

from framework import sentry
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
        user_guid = self.request.user._id

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
        _global_reviews = [
            NotificationType.Type.PROVIDER_NEW_PENDING_SUBMISSIONS.value,
            NotificationType.Type.PROVIDER_REVIEWS_SUBMISSION_CONFIRMATION.value,
            NotificationType.Type.PROVIDER_REVIEWS_RESUBMISSION_CONFIRMATION.value,
            NotificationType.Type.PROVIDER_NEW_PENDING_WITHDRAW_REQUESTS.value,
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

        qs = NotificationSubscription.objects.filter(
            notification_type__name__in=[
                NotificationType.Type.USER_FILE_UPDATED.value,
                NotificationType.Type.NODE_FILE_UPDATED.value,
                NotificationType.Type.PROVIDER_NEW_PENDING_SUBMISSIONS.value,
            ] + _global_reviews + _global_file_updated + _node_file_updated,
            user=self.request.user,
        ).annotate(
            event_name=Case(
                When(
                    notification_type__name__in=_node_file_updated,
                    then=Value('files_updated'),
                ),
                When(
                    notification_type__name__in=_global_file_updated,
                    then=Value('global_file_updated'),
                ),
                When(
                    notification_type__name__in=_global_reviews,
                    then=Value('global_reviews'),
                ),
                default=Value('notification_type__name'),
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
                    notification_type__name__in=_global_reviews,
                    then=Value(f'{user_guid}_global_reviews'),
                ),
                default=Value('notification_type__name'),
            ),
        ).distinct('legacy_id')

        # Apply manual filter for legacy_id if requested
        filter_id = self.request.query_params.get('filter[id]')
        if filter_id:
            qs = qs.filter(legacy_id=filter_id)
            # convert to list comprehension because legacy_id is an annotation, not in DB
        # Apply manual filter for event_name if requested
        filter_event_name = self.request.query_params.get('filter[event_name]')
        if filter_event_name:
            qs = qs.filter(event_name__in=filter_event_name.split(','))

        return qs

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
        user_file_updated_nt = NotificationType.Type.USER_FILE_UPDATED.instance
        reviews_submission_status_nt = NotificationType.Type.REVIEWS_SUBMISSION_STATUS.instance
        node_file_updated_nt = NotificationType.Type.NODE_FILE_UPDATED.instance
        user_ct = ContentType.objects.get_for_model(OSFUser)
        node_ct = ContentType.objects.get_for_model(AbstractNode)
        provider_ct = ContentType.objects.get_for_model(AbstractProvider)

        node_subquery = AbstractNode.objects.filter(
            id=Cast(OuterRef('object_id'), IntegerField()),
        ).values('guids___id')[:1]

        node_guid = 'n/a'
        missing_subscription_created = None
        annotated_obj_qs = NotificationSubscription.objects.filter(user=self.request.user).annotate(
            legacy_id=Case(
                When(
                    notification_type__name=NotificationType.Type.NODE_FILE_UPDATED.value,
                    content_type=node_ct,
                    then=Concat(Subquery(node_subquery), Value('_files_updated')),
                ),
                When(
                    notification_type__name=NotificationType.Type.USER_FILE_UPDATED.value,
                    then=Value(f'{user_guid}_global_file_updated'),
                ),
                When(
                    notification_type__name=NotificationType.Type.PROVIDER_NEW_PENDING_SUBMISSIONS.value,
                    content_type=provider_ct,
                    then=Value(f'{user_guid}_global_reviews'),
                ),
                default=Value(f'{user_guid}_global'),
                output_field=CharField(),
            ),
        )
        existing_subscriptions = annotated_obj_qs.filter(legacy_id=subscription_id)
        if not existing_subscriptions.exists():
            # `global_file_updated` and `global_reviews` should exist by default for every user.
            # If not found, create them with `none` frequency and `_is_digest=True` as default.
            if subscription_id == f'{user_guid}_global_file_updated':
                notification_type = user_file_updated_nt
                content_type = user_ct
                object_id = self.request.user.id
            elif subscription_id == f'{user_guid}_global_reviews':
                notification_type = reviews_submission_status_nt
                content_type = user_ct
                object_id = self.request.user.id
            elif subscription_id.endswith('_global_file_updated') or subscription_id.endswith('_global_reviews'):
                # Mismatched request user and subscription user
                sentry.log_message(f'Permission denied: [user={user_guid}, legacy_id={subscription_id}]')
                raise PermissionDenied
            elif subscription_id.endswith('_file_updated'):
                notification_type = node_file_updated_nt
                content_type = node_ct
                node_guid = subscription_id[:-len('_file_updated')]
                node = AbstractNode.objects.filter(guids___id=node_guid, is_deleted=False, type='osf.node').first()
                if not node:
                    # The node in the legacy subscription ID does not exist or is invalid
                    sentry.log_message(f'Node not found in legacy subscription ID: [user={user_guid}, legacy_id={subscription_id}]')
                    raise NotFound
                if not node.is_contributor(self.request.user):
                    # The request user is not a contributor of the node
                    sentry.log_message(f'Permission denied: [user={user_guid}], node={node_guid}, legacy_id={subscription_id}]')
                    raise PermissionDenied
                object_id = node.id
            else:
                sentry.log_message(f'Subscription not found: [user={user_guid}, legacy_id={subscription_id}]')
                raise NotFound
            missing_subscription_created = NotificationSubscription.objects.create(
                notification_type=notification_type,
                user=self.request.user,
                content_type=content_type,
                object_id=object_id,
                _is_digest=True,
                message_frequency='none',
            )
            sentry.log_message(f'Missing default subscription has been created: [user={user_guid}], node={node_guid} type={notification_type}, legacy_id={subscription_id}]')

        if missing_subscription_created:
            subscription = missing_subscription_created
        else:
            subscription = existing_subscriptions.filter(user=self.request.user).order_by('id').last()
            if not subscription:
                raise PermissionDenied

        self.check_object_permissions(self.request, subscription)
        return subscription

    def update(self, request, *args, **kwargs):
        """
        Update a notification subscription
        """
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
        elif '_files_updated' in self.kwargs['subscription_id']:
            # Copy _files_updated subscription changes to all node file subscriptions
            node_id = Guid.load(self.kwargs['subscription_id'].split('_files_updated')[0]).object_id

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

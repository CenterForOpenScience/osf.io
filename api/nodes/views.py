import re

from distutils.version import StrictVersion
from django.apps import apps
from django.db.models import Q, OuterRef, Exists, Subquery, F
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType
from rest_framework import generics, permissions as drf_permissions
from rest_framework.exceptions import PermissionDenied, ValidationError, NotFound, MethodNotAllowed, NotAuthenticated
from rest_framework.response import Response
from rest_framework.status import HTTP_202_ACCEPTED, HTTP_204_NO_CONTENT

from addons.base.exceptions import InvalidAuthError
from addons.osfstorage.models import OsfStorageFolder
from api.addons.serializers import NodeAddonFolderSerializer
from api.addons.views import AddonSettingsMixin
from api.base import generic_bulk_views as bulk_views
from api.base import permissions as base_permissions
from api.base.exceptions import (
    InvalidModelValueError,
    JSONAPIException,
    Gone,
    RelationshipPostMakesNoChanges,
    EndpointNotImplementedError,
    InvalidQueryStringError,
    PermanentlyMovedError,
)
from api.base.filters import ListFilterMixin, PreprintFilterMixin
from api.base.pagination import CommentPagination, NodeContributorPagination, MaxSizePagination
from api.base.parsers import (
    JSONAPIRelationshipParser,
    JSONAPIRelationshipParserForRegularJSON,
    JSONAPIMultipleRelationshipsParser,
    JSONAPIMultipleRelationshipsParserForRegularJSON,
)
from api.base.settings import ADDONS_OAUTH, API_BASE
from api.base.throttling import (
    UserRateThrottle,
    NonCookieAuthThrottle,
    AddContributorThrottle,
    BurstRateThrottle,
    FilesRateThrottle,
    FilesBurstRateThrottle,
)
from api.base.utils import default_node_list_permission_queryset
from api.base.utils import get_object_or_error, is_bulk_request, get_user_auth, is_truthy
from api.base.versioning import DRAFT_REGISTRATION_SERIALIZERS_UPDATE_VERSION
from api.base.views import JSONAPIBaseView
from api.base.views import (
    BaseChildrenList,
    BaseContributorDetail,
    BaseContributorList,
    BaseLinkedList,
    BaseNodeLinksDetail,
    BaseNodeLinksList,
    LinkedNodesRelationship,
    LinkedRegistrationsRelationship,
    WaterButlerMixin,
)
from api.base.waffle_decorators import require_flag
from api.citations.utils import render_citation
from api.comments.permissions import CanCommentOrPublic
from api.comments.serializers import (
    CommentCreateSerializer,
    NodeCommentSerializer,
)
from api.draft_registrations.serializers import DraftRegistrationSerializer, DraftRegistrationDetailSerializer
from api.files.serializers import FileSerializer, OsfStorageFileSerializer
from api.identifiers.serializers import NodeIdentifierSerializer
from api.identifiers.views import IdentifierList
from api.institutions.serializers import InstitutionSerializer
from api.logs.serializers import NodeLogSerializer
from api.nodes.filters import NodesFilterMixin
from api.nodes.permissions import (
    IsAdmin,
    IsAdminContributor,
    IsPublic,
    AdminOrPublic,
    WriteAdmin,
    ContributorOrPublic,
    AdminContributorOrPublic,
    RegistrationAndPermissionCheckForPointers,
    ContributorDetailPermissions,
    ReadOnlyIfRegistration,
    NodeGroupDetailPermissions,
    IsContributorOrGroupMember,
    AdminDeletePermissions,
    WriteOrPublicForRelationshipInstitutions,
    ExcludeWithdrawals,
    NodeLinksShowIfVersion,
    ReadOnlyIfWithdrawn,
)
from api.nodes.serializers import (
    NodeSerializer,
    ForwardNodeAddonSettingsSerializer,
    NodeAddonSettingsSerializer,
    NodeLinksSerializer,
    NodeForksSerializer,
    NodeDetailSerializer,
    NodeStorageProviderSerializer,
    DraftRegistrationLegacySerializer,
    DraftRegistrationDetailLegacySerializer,
    NodeContributorsSerializer,
    NodeContributorDetailSerializer,
    NodeInstitutionsRelationshipSerializer,
    NodeContributorsCreateSerializer,
    NodeViewOnlyLinkSerializer,
    NodeViewOnlyLinkUpdateSerializer,
    NodeSettingsSerializer,
    NodeSettingsUpdateSerializer,
    NodeStorageSerializer,
    NodeCitationSerializer,
    NodeCitationStyleSerializer,
    NodeGroupsSerializer,
    NodeGroupsCreateSerializer,
    NodeGroupsDetailSerializer,
)
from api.nodes.utils import NodeOptimizationMixin, enforce_no_children
from api.osf_groups.views import OSFGroupMixin
from api.preprints.serializers import PreprintSerializer
from api.registrations.serializers import (
    RegistrationSerializer,
    RegistrationCreateSerializer,
)
from api.requests.permissions import NodeRequestPermission
from api.requests.serializers import NodeRequestSerializer, NodeRequestCreateSerializer
from api.requests.views import NodeRequestMixin
from api.subjects.views import SubjectRelationshipBaseView, BaseResourceSubjectsList
from api.users.views import UserMixin
from api.users.serializers import UserSerializer
from api.wikis.serializers import NodeWikiSerializer
from framework.exceptions import HTTPError, PermissionsError
from framework.auth.oauth_scopes import CoreScopes
from framework.sentry import log_exception
from osf.features import OSF_GROUPS
from osf.models import AbstractNode
from osf.models import (Node, PrivateLink, Institution, Comment, DraftRegistration, Registration, )
from osf.models import OSFUser
from osf.models import OSFGroup
from osf.models import NodeRelation, Guid
from osf.models import BaseFileNode
from osf.models.files import File, Folder
from addons.osfstorage.models import Region
from osf.utils.permissions import ADMIN, WRITE_NODE
from website import mails, settings

# This is used to rethrow v1 exceptions as v2
HTTP_CODE_MAP = {
    400: ValidationError(detail='This add-on has made a bad request.'),
    401: NotAuthenticated('This add-on could not be authenticated.'),
    403: PermissionDenied('This add-on\'s credentials could not be validated.'),
    404: NotFound('This add-on\'s resources could not be found.'),
}


class NodeMixin(object):
    """Mixin with convenience methods for retrieving the current node based on the
    current URL. By default, fetches the current node based on the node_id kwarg.
    """

    serializer_class = NodeSerializer
    node_lookup_url_kwarg = 'node_id'

    def get_node(self, check_object_permissions=True, node_id=None):
        node = None

        if self.kwargs.get('is_embedded') is True:
            # If this is an embedded request, the node might be cached somewhere
            node = self.request.parents[Node].get(self.kwargs[self.node_lookup_url_kwarg])

        node_id = node_id or self.kwargs[self.node_lookup_url_kwarg]
        if node is None:
            node = get_object_or_error(
                Node.objects.filter(guids___id=node_id).annotate(region=F('addons_osfstorage_node_settings__region___id')).exclude(region=None),
                request=self.request,
                display_name='node',
            )
        # Nodes that are folders/collections are treated as a separate resource, so if the client
        # requests a collection through a node endpoint, we return a 404
        if node.is_collection or node.is_registration:
            raise NotFound
        # May raise a permission denied
        if check_object_permissions:
            self.check_object_permissions(self.request, node)
        return node


class DraftMixin(object):

    serializer_class = DraftRegistrationLegacySerializer

    def check_branched_from(self, draft):
        node_id = self.kwargs['node_id']

        if not draft.branched_from._id == node_id:
            raise ValidationError('This draft registration is not created from the given node.')

    def check_resource_permissions(self, resource):
        # If branched from a node, use the node's contributor permissions. See [ENG-1563]
        if resource.branched_from_type == 'Node':
            resource = resource.branched_from
        return self.check_object_permissions(self.request, resource)

    def get_draft(self, draft_id=None, check_object_permissions=True):
        if draft_id is None:
            draft_id = self.kwargs['draft_id']
        draft = get_object_or_error(DraftRegistration, draft_id, self.request)

        self.check_branched_from(draft)

        if self.request.method not in drf_permissions.SAFE_METHODS:
            registered_and_deleted = draft.registered_node and draft.registered_node.is_deleted

            if draft.registered_node and not draft.registered_node.is_deleted:
                raise PermissionDenied('This draft has already been registered and cannot be modified.')

            if draft.is_pending_review:
                raise PermissionDenied('This draft is pending review and cannot be modified.')

            if draft.requires_approval and draft.is_approved and (not registered_and_deleted):
                raise PermissionDenied('This draft has already been approved and cannot be modified.')
        else:
            if draft.registered_node and not draft.registered_node.is_deleted:
                redirect_url = draft.registered_node.absolute_api_v2_url
                self.headers['location'] = redirect_url
                raise PermanentlyMovedError(detail='Draft has already been registered')

        if check_object_permissions:
            self.check_resource_permissions(draft)

        return draft


class NodeList(JSONAPIBaseView, bulk_views.BulkUpdateJSONAPIView, bulk_views.BulkDestroyJSONAPIView, bulk_views.ListBulkCreateJSONAPIView, NodesFilterMixin, WaterButlerMixin, NodeOptimizationMixin):
    """The documentation for this endpoint can be found [here](https://developer.osf.io/#operation/nodes_list).
    """
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.NODE_BASE_READ]
    required_write_scopes = [CoreScopes.NODE_BASE_WRITE]
    model_class = apps.get_model('osf.AbstractNode')

    parser_classes = (JSONAPIMultipleRelationshipsParser, JSONAPIMultipleRelationshipsParserForRegularJSON,)
    serializer_class = NodeSerializer
    view_category = 'nodes'
    view_name = 'node-list'

    ordering = ('-modified', )  # default ordering

    # overrides NodesFilterMixin
    def get_default_queryset(self):
        return default_node_list_permission_queryset(user=self.request.user, model_cls=Node)

    # overrides ListBulkCreateJSONAPIView, BulkUpdateJSONAPIView
    def get_queryset(self):
        # For bulk requests, queryset is formed from request body.
        if is_bulk_request(self.request):
            auth = get_user_auth(self.request)
            nodes = Node.objects.filter(guids___id__in=[node['id'] for node in self.request.data])

            # If skip_uneditable=True in query_params, skip nodes for which the user
            # does not have EDIT permissions.
            if is_truthy(self.request.query_params.get('skip_uneditable', False)):
                return Node.objects.get_nodes_for_user(auth.user, WRITE_NODE, nodes)

            for node in nodes:
                if not node.can_edit(auth):
                    raise PermissionDenied
            return nodes
        else:
            return self.get_queryset_from_request()

    # overrides ListBulkCreateJSONAPIView, BulkUpdateJSONAPIView, BulkDestroyJSONAPIView
    def get_serializer_class(self):
        """
        Use NodeDetailSerializer which requires 'id'
        """
        if self.request.method in ('PUT', 'PATCH', 'DELETE'):
            return NodeDetailSerializer
        else:
            return NodeSerializer

    def get_serializer_context(self):
        context = super(NodeList, self).get_serializer_context()
        region_id = self.request.query_params.get('region', None)
        if region_id:
            try:
                region_id = Region.objects.filter(_id=region_id).values_list('id', flat=True).get()
            except Region.DoesNotExist:
                raise InvalidQueryStringError('Region {} is invalid.'.format(region_id))
            context.update({
                'region_id': region_id,
            })
        return context

    # overrides ListBulkCreateJSONAPIView
    def perform_create(self, serializer):
        """Create a node.

        :param serializer:
        """
        # On creation, make sure that current user is the creator
        user = self.request.user
        serializer.save(creator=user)

    # overrides BulkDestroyJSONAPIView
    def allow_bulk_destroy_resources(self, user, resource_list):
        """User must have admin permissions to delete nodes."""
        if is_truthy(self.request.query_params.get('skip_uneditable', False)):
            return any([node.has_permission(user, ADMIN) for node in resource_list])
        return all([node.has_permission(user, ADMIN) for node in resource_list])

    def bulk_destroy_skip_uneditable(self, resource_object_list, user, object_type):
        """
        If skip_uneditable=True in query_params, skip the resources for which the user does not have
        admin permissions and delete the remaining resources
        """
        allowed = []
        skipped = []

        if not is_truthy(self.request.query_params.get('skip_uneditable', False)):
            return None

        for resource in resource_object_list:
            if resource.has_permission(user, ADMIN):
                allowed.append(resource)
            else:
                skipped.append({'id': resource._id, 'type': object_type})

        return {'skipped': skipped, 'allowed': allowed}

    # Overrides BulkDestroyModelMixin
    def perform_bulk_destroy(self, resource_object_list):
        if enforce_no_children(self.request):
            if NodeRelation.objects.filter(
                parent__in=resource_object_list,
                child__is_deleted=False,
            ).exclude(Q(child__in=resource_object_list) | Q(is_node_link=True)).exists():
                raise ValidationError('Any child components must be deleted prior to deleting this project.')

        for node in resource_object_list:
            self.perform_destroy(node)

    # Overrides BulkDestroyModelMixin
    def perform_destroy(self, instance):
        auth = get_user_auth(self.request)
        try:
            instance.remove_node(auth=auth)
        except PermissionsError as err:
            raise PermissionDenied(str(err))


class NodeDetail(JSONAPIBaseView, generics.RetrieveUpdateDestroyAPIView, NodeMixin, WaterButlerMixin):
    """The documentation for this endpoint can be found [here](https://developer.osf.io/#operation/nodes_read).
    """
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        ContributorOrPublic,
        AdminDeletePermissions,
        ReadOnlyIfRegistration,
        base_permissions.TokenHasScope,
        ExcludeWithdrawals,
    )

    required_read_scopes = [CoreScopes.NODE_BASE_READ]
    required_write_scopes = [CoreScopes.NODE_BASE_WRITE]

    parser_classes = (JSONAPIMultipleRelationshipsParser, JSONAPIMultipleRelationshipsParserForRegularJSON,)

    serializer_class = NodeDetailSerializer
    view_category = 'nodes'
    view_name = 'node-detail'

    # overrides RetrieveUpdateDestroyAPIView
    def get_object(self):
        return self.get_node()

    # overrides RetrieveUpdateDestroyAPIView
    def perform_destroy(self, instance):
        auth = get_user_auth(self.request)
        node = self.get_object()

        if enforce_no_children(self.request) and Node.objects.get_children(node, active=True).exists():
            raise ValidationError('Any child components must be deleted prior to deleting this project.')

        try:
            node.remove_node(auth=auth)
        except PermissionsError as err:
            raise PermissionDenied(str(err))

    def get_renderer_context(self):
        context = super(NodeDetail, self).get_renderer_context()
        show_counts = is_truthy(self.request.query_params.get('related_counts', False))
        if show_counts:
            node = self.get_object()
            context['meta'] = {
                'templated_by_count': node.templated_list.count(),
            }
        return context


class NodeContributorsList(BaseContributorList, bulk_views.BulkUpdateJSONAPIView, bulk_views.BulkDestroyJSONAPIView, bulk_views.ListBulkCreateJSONAPIView, NodeMixin):
    """The documentation for this endpoint can be found [here](https://developer.osf.io/#operation/nodes_contributors_list).
    """
    permission_classes = (
        AdminOrPublic,
        drf_permissions.IsAuthenticatedOrReadOnly,
        ReadOnlyIfRegistration,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.NODE_CONTRIBUTORS_READ]
    required_write_scopes = [CoreScopes.NODE_CONTRIBUTORS_WRITE]
    model_class = OSFUser

    throttle_classes = (AddContributorThrottle, UserRateThrottle, NonCookieAuthThrottle, BurstRateThrottle, )

    pagination_class = NodeContributorPagination
    serializer_class = NodeContributorsSerializer
    view_category = 'nodes'
    view_name = 'node-contributors'
    ordering = ('_order',)  # default ordering

    def get_resource(self):
        return self.get_node()

    # overrides ListBulkCreateJSONAPIView, BulkUpdateJSONAPIView, BulkDeleteJSONAPIView
    def get_serializer_class(self):
        """
        Use NodeContributorDetailSerializer which requires 'id'
        """
        if self.request.method == 'PUT' or self.request.method == 'PATCH' or self.request.method == 'DELETE':
            return NodeContributorDetailSerializer
        elif self.request.method == 'POST':
            return NodeContributorsCreateSerializer
        else:
            return NodeContributorsSerializer

    # overrides ListBulkCreateJSONAPIView, BulkUpdateJSONAPIView
    def get_queryset(self):
        queryset = self.get_queryset_from_request()
        # If bulk request, queryset only contains contributors in request
        if is_bulk_request(self.request):
            contrib_ids = []
            for item in self.request.data:
                try:
                    contrib_ids.append(item['id'].split('-')[1])
                except AttributeError:
                    raise ValidationError('Contributor identifier not provided.')
                except IndexError:
                    raise ValidationError('Contributor identifier incorrectly formatted.')
            queryset = queryset.filter(user__guids___id__in=contrib_ids)
        return queryset

    # Overrides BulkDestroyJSONAPIView
    def perform_destroy(self, instance):
        auth = get_user_auth(self.request)
        node = self.get_resource()
        if len(node.visible_contributors) == 1 and node.get_visible(instance):
            raise ValidationError('Must have at least one visible contributor')
        if not node.contributor_set.filter(user=instance).exists():
            raise NotFound('User cannot be found in the list of contributors.')
        removed = node.remove_contributor(instance, auth)
        if not removed:
            raise ValidationError('Must have at least one registered admin contributor')

    # Overrides BulkDestroyJSONAPIView
    def get_requested_resources(self, request, request_data):
        requested_ids = []
        for data in request_data:
            try:
                requested_ids.append(data['id'].split('-')[1])
            except IndexError:
                raise ValidationError('Contributor identifier incorrectly formatted.')

        resource_object_list = OSFUser.objects.filter(guids___id__in=requested_ids)
        for resource in resource_object_list:
            if getattr(resource, 'is_deleted', None):
                raise Gone

        if len(resource_object_list) != len(request_data):
            raise ValidationError({'non_field_errors': 'Could not find all objects to delete.'})

        return resource_object_list

    def get_serializer_context(self):
        context = JSONAPIBaseView.get_serializer_context(self)
        context['resource'] = self.get_resource()
        context['default_email'] = 'default'
        return context


class NodeContributorDetail(BaseContributorDetail, generics.RetrieveUpdateDestroyAPIView, NodeMixin, UserMixin):
    """The documentation for this endpoint can be found [here](https://developer.osf.io/#operation/nodes_contributors_read).
    """
    permission_classes = (
        ContributorDetailPermissions,
        drf_permissions.IsAuthenticatedOrReadOnly,
        ReadOnlyIfRegistration,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.NODE_CONTRIBUTORS_READ]
    required_write_scopes = [CoreScopes.NODE_CONTRIBUTORS_WRITE]

    serializer_class = NodeContributorDetailSerializer
    view_category = 'nodes'
    view_name = 'node-contributor-detail'

    def get_resource(self):
        return self.get_node()

    # overrides DestroyAPIView
    def perform_destroy(self, instance):
        node = self.get_resource()
        auth = get_user_auth(self.request)
        if len(node.visible_contributors) == 1 and instance.visible:
            raise ValidationError('Must have at least one visible contributor')
        removed = node.remove_contributor(instance, auth)
        if not removed:
            raise ValidationError('Must have at least one registered admin contributor')

    def get_serializer_context(self):
        context = JSONAPIBaseView.get_serializer_context(self)
        context['resource'] = self.get_resource()
        context['default_email'] = 'default'
        return context


class NodeImplicitContributorsList(JSONAPIBaseView, generics.ListAPIView, ListFilterMixin, NodeMixin):
    permission_classes = (
        AdminOrPublic,
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.NODE_CONTRIBUTORS_READ]
    required_write_scopes = [CoreScopes.NULL]

    model_class = OSFUser

    throttle_classes = (UserRateThrottle, NonCookieAuthThrottle, BurstRateThrottle, )

    serializer_class = UserSerializer
    view_category = 'nodes'
    view_name = 'node-implicit-contributors'
    ordering = ('_order',)  # default ordering

    def get_default_queryset(self):
        node = self.get_node()

        return node.parent_admin_contributors

    def get_queryset(self):
        queryset = self.get_queryset_from_request()
        return queryset


class NodeContributorsAndGroupMembersList(JSONAPIBaseView, generics.ListAPIView, ListFilterMixin, NodeMixin):
    permission_classes = (
        AdminOrPublic,
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.NODE_CONTRIBUTORS_READ]
    required_write_scopes = [CoreScopes.NULL]

    model_class = OSFUser

    serializer_class = UserSerializer
    view_category = 'nodes'
    view_name = 'node-contributors-and-group-members'

    def get_default_queryset(self):
        return self.get_node().contributors_and_group_members

    def get_queryset(self):
        queryset = self.get_queryset_from_request()
        return queryset


class NodeBibliographicContributorsList(BaseContributorList, NodeMixin):
    permission_classes = (
        AdminOrPublic,
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.NODE_CONTRIBUTORS_READ]
    required_write_scopes = [CoreScopes.NULL]

    model_class = OSFUser

    throttle_classes = (UserRateThrottle, NonCookieAuthThrottle, BurstRateThrottle, )

    pagination_class = NodeContributorPagination
    serializer_class = NodeContributorsSerializer
    view_category = 'nodes'
    view_name = 'node-bibliographic-contributors'
    ordering = ('_order',)  # default ordering

    def get_resource(self):
        return self.get_node()

    def get_default_queryset(self):
        contributors = super(NodeBibliographicContributorsList, self).get_default_queryset()
        return contributors.filter(visible=True)


class NodeDraftRegistrationsList(JSONAPIBaseView, generics.ListCreateAPIView, NodeMixin):
    """
    The documentation for this endpoint can be found [here](https://developer.osf.io/#operation/nodes_draft_registrations_list).
    This endpoint supports the older registries submission workflow and will soon be deprecated.
    Use DraftRegistrationsList endpoint instead.
    """
    permission_classes = (
        IsAdminContributor,
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    parser_classes = (JSONAPIMultipleRelationshipsParser, JSONAPIMultipleRelationshipsParserForRegularJSON,)

    required_read_scopes = [CoreScopes.NODE_DRAFT_REGISTRATIONS_READ]
    required_write_scopes = [CoreScopes.NODE_DRAFT_REGISTRATIONS_WRITE]

    serializer_class = DraftRegistrationLegacySerializer
    view_category = 'nodes'
    view_name = 'node-draft-registrations'

    ordering = ('-modified',)

    def get_serializer_class(self):
        if StrictVersion(getattr(self.request, 'version', '2.0')) >= StrictVersion(DRAFT_REGISTRATION_SERIALIZERS_UPDATE_VERSION):
            return DraftRegistrationSerializer
        return DraftRegistrationLegacySerializer

    # overrides ListCreateAPIView
    def get_queryset(self):
        node = self.get_node()
        return node.draft_registrations_active


class NodeDraftRegistrationDetail(JSONAPIBaseView, generics.RetrieveUpdateDestroyAPIView, DraftMixin):
    """
    The documentation for this endpoint can be found [here](https://developer.osf.io/#operation/nodes_draft_registrations_read).
    This endpoint supports the older registries submission workflow and will soon be deprecated.
    Use DraftRegistrationDetail endpoint instead.
    """
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
        IsAdminContributor,
    )
    parser_classes = (JSONAPIMultipleRelationshipsParser, JSONAPIMultipleRelationshipsParserForRegularJSON,)

    required_read_scopes = [CoreScopes.NODE_DRAFT_REGISTRATIONS_READ]
    required_write_scopes = [CoreScopes.NODE_DRAFT_REGISTRATIONS_WRITE]

    serializer_class = DraftRegistrationDetailLegacySerializer
    view_category = 'nodes'
    view_name = 'node-draft-registration-detail'

    def get_serializer_class(self):
        if StrictVersion(getattr(self.request, 'version', '2.0')) >= StrictVersion(DRAFT_REGISTRATION_SERIALIZERS_UPDATE_VERSION):
            return DraftRegistrationDetailSerializer
        return DraftRegistrationDetailLegacySerializer

    def get_object(self):
        return self.get_draft()

    def perform_destroy(self, draft):
        draft.deleted = timezone.now()
        draft.save(update_fields=['deleted'])


class NodeRegistrationsList(JSONAPIBaseView, generics.ListCreateAPIView, NodeMixin, DraftMixin):
    """The documentation for this endpoint can be found [here](https://developer.osf.io/#operation/nodes_registrations_list).
    """
    permission_classes = (
        AdminContributorOrPublic,
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
        ExcludeWithdrawals,
    )

    required_read_scopes = [CoreScopes.NODE_REGISTRATIONS_READ]
    required_write_scopes = [CoreScopes.NODE_REGISTRATIONS_WRITE]

    serializer_class = RegistrationSerializer
    view_category = 'nodes'
    view_name = 'node-registrations'

    ordering = ('-modified',)

    def get_serializer_class(self):
        if self.request.method in ('PUT', 'POST'):
            return RegistrationCreateSerializer
        return RegistrationSerializer

    # overrides ListCreateAPIView
    # TODO: Filter out withdrawals by default
    def get_queryset(self):
        nodes = self.get_node().registrations_all
        auth = get_user_auth(self.request)
        registrations = [node for node in nodes if node.can_view(auth)]
        return registrations

    # overrides ListCreateJSONAPIView
    def perform_create(self, serializer):
        """Create a registration from a draft.
        """
        # On creation, make sure that current user is the creator
        draft_id = self.request.data.get('draft_registration', None) or self.request.data.get('draft_registration_id', None)
        draft = self.get_draft(draft_id)
        try:
            serializer.save(draft=draft)
        except ValidationError as e:
            log_exception()
            raise e


class NodeChildrenList(BaseChildrenList, bulk_views.ListBulkCreateJSONAPIView, NodeMixin):
    """The documentation for this endpoint can be found [here](https://developer.osf.io/#operation/nodes_children_list).
    """

    required_read_scopes = [CoreScopes.NODE_CHILDREN_READ]
    required_write_scopes = [CoreScopes.NODE_CHILDREN_WRITE]

    serializer_class = NodeSerializer
    view_category = 'nodes'
    view_name = 'node-children'
    model_class = Node

    def get_serializer_context(self):
        context = super(NodeChildrenList, self).get_serializer_context()
        region__id = self.request.query_params.get('region', None)
        id = None
        if region__id:
            try:
                id = Region.objects.filter(_id=region__id).values_list('id', flat=True).get()
            except Region.DoesNotExist:
                raise InvalidQueryStringError('Region {} is invalid.'.format(region__id))

        context.update({
            'region_id': id,
        })
        return context

    # overrides ListBulkCreateJSONAPIView
    def perform_create(self, serializer):
        user = self.request.user
        serializer.save(creator=user, parent=self.get_node())


class NodeCitationDetail(JSONAPIBaseView, generics.RetrieveAPIView, NodeMixin):
    """The documentation for this endpoint can be found [here](https://developer.osf.io/#operation/nodes_citation_list).
    """
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.NODE_CITATIONS_READ]
    required_write_scopes = [CoreScopes.NODE_CITATIONS_WRITE]

    serializer_class = NodeCitationSerializer
    view_category = 'nodes'
    view_name = 'node-citation'

    def get_object(self):
        node = self.get_node()
        auth = get_user_auth(self.request)
        if not node.is_public and not node.can_view(auth):
            raise PermissionDenied if auth.user else NotAuthenticated
        return node.csl

class NodeCitationStyleDetail(JSONAPIBaseView, generics.RetrieveAPIView, NodeMixin):
    """ The documentation for this endpoint can be found [here](https://developer.osf.io/#operation/nodes_citation_read).
    """
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.NODE_CITATIONS_READ]
    required_write_scopes = [CoreScopes.NULL]

    serializer_class = NodeCitationStyleSerializer
    view_category = 'nodes'
    view_name = 'node-citation'

    def get_object(self):
        node = self.get_node()
        auth = get_user_auth(self.request)
        if not node.is_public and not node.can_view(auth):
            raise PermissionDenied if auth.user else NotAuthenticated

        style = self.kwargs.get('style_id')
        try:
            citation = render_citation(node=node, style=style)
        except ValueError as err:  # style requested could not be found
            csl_name = re.findall(r'[a-zA-Z]+\.csl', str(err))[0]
            raise NotFound('{} is not a known style.'.format(csl_name))

        return {'citation': citation, 'id': style}


# TODO: Make NodeLinks filterable. They currently aren't filterable because we have can't
# currently query on a Pointer's node's attributes.
# e.g. Pointer.find(MQ('node.title', 'eq', ...)) doesn't work
class NodeLinksList(BaseNodeLinksList, bulk_views.BulkDestroyJSONAPIView, bulk_views.ListBulkCreateJSONAPIView, NodeMixin):
    """Node Links to other nodes. *Writeable*.

    Node Links act as pointers to other nodes. Unlike Forks, they are not copies of nodes;
    Node Links are a direct reference to the node that they point to.

    ##Node Link Attributes
    `type` is "node_links"

        None

    ##Links

    See the [JSON-API spec regarding pagination](http://jsonapi.org/format/1.0/#fetching-pagination).

    ##Relationships

    ### Target Node

    This endpoint shows the target node detail and is automatically embedded.

    ##Actions

    ###Adding Node Links
        Method:        POST
        URL:           /links/self
        Query Params:  <none>
        Body (JSON): {
                       "data": {
                          "type": "node_links",                  # required
                          "relationships": {
                            "nodes": {
                              "data": {
                                "type": "nodes",                 # required
                                "id": "{target_node_id}",        # required
                              }
                            }
                          }
                       }
                    }
        Success:       201 CREATED + node link representation

    To add a node link (a pointer to another node), issue a POST request to this endpoint.  This effectively creates a
    relationship between the node and the target node.  The target node must be described as a relationship object with
    a "data" member, containing the nodes `type` and the target node `id`.

    ##Query Params

    + `page=<Int>` -- page number of results to view, default 1

    + `filter[<fieldname>]=<Str>` -- fields and values to filter the search results on.

    #This Request/Response
    """
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        ContributorOrPublic,
        base_permissions.TokenHasScope,
        ExcludeWithdrawals,
        NodeLinksShowIfVersion,
    )

    required_read_scopes = [CoreScopes.NODE_LINKS_READ]
    required_write_scopes = [CoreScopes.NODE_LINKS_WRITE]
    model_class = NodeRelation

    serializer_class = NodeLinksSerializer
    view_category = 'nodes'
    view_name = 'node-pointers'

    def get_queryset(self):
        return self.get_node().node_relations.select_related('child').filter(is_node_link=True, child__is_deleted=False)

    # Overrides BulkDestroyJSONAPIView
    def perform_destroy(self, instance):
        auth = get_user_auth(self.request)
        node = get_object_or_error(
            Node,
            self.kwargs[self.node_lookup_url_kwarg],
            self.request,
            display_name='node',
        )
        if node.is_registration:
            raise MethodNotAllowed(method=self.request.method)
        node = self.get_node()
        try:
            node.rm_pointer(instance, auth=auth)
        except ValueError as err:  # pointer doesn't belong to node
            raise ValidationError(str(err))
        node.save()

    # overrides ListCreateAPIView
    def get_parser_context(self, http_request):
        """
        Tells parser that we are creating a relationship
        """
        res = super(NodeLinksList, self).get_parser_context(http_request)
        res['is_relationship'] = True
        return res


class NodeLinksDetail(BaseNodeLinksDetail, generics.RetrieveDestroyAPIView, NodeMixin):
    """Node Link details. *Writeable*.

    Node Links act as pointers to other nodes. Unlike Forks, they are not copies of nodes;
    Node Links are a direct reference to the node that they point to.

    ##Attributes
    `type` is "node_links"

        None

    ##Links

    *None*

    ##Relationships

    ###Target node

    This endpoint shows the target node detail and is automatically embedded.

    ##Actions

    ###Remove Node Link

        Method:        DELETE
        URL:           /links/self
        Query Params:  <none>
        Success:       204 No Content

    To remove a node link from a node, issue a DELETE request to the `self` link.  This request will remove the
    relationship between the node and the target node, not the nodes themselves.

    ##Query Params

    *None*.

    #This Request/Response
    """
    permission_classes = (
        base_permissions.TokenHasScope,
        drf_permissions.IsAuthenticatedOrReadOnly,
        RegistrationAndPermissionCheckForPointers,
        ExcludeWithdrawals,
        NodeLinksShowIfVersion,
    )

    required_read_scopes = [CoreScopes.NODE_LINKS_READ]
    required_write_scopes = [CoreScopes.NODE_LINKS_WRITE]

    serializer_class = NodeLinksSerializer
    view_category = 'nodes'
    view_name = 'node-pointer-detail'
    node_link_lookup_url_kwarg = 'node_link_id'

    # overrides RetrieveAPIView
    def get_object(self):
        node_link = get_object_or_error(
            NodeRelation,
            self.kwargs[self.node_link_lookup_url_kwarg],
            self.request,
            'node link',
        )
        self.check_object_permissions(self.request, node_link.parent)
        return node_link

    # overrides DestroyAPIView
    def perform_destroy(self, instance):
        auth = get_user_auth(self.request)
        node = self.get_node()
        pointer = self.get_object()
        try:
            node.rm_pointer(pointer, auth=auth)
        except ValueError as err:  # pointer doesn't belong to node
            raise NotFound(str(err))
        node.save()


class NodeForksList(JSONAPIBaseView, generics.ListCreateAPIView, NodeMixin, NodesFilterMixin):
    """The documentation for this endpoint can be found [here](https://developer.osf.io/#operation/nodes_forks_list).
    """
    permission_classes = (
        IsPublic,
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
        ExcludeWithdrawals,
    )

    required_read_scopes = [CoreScopes.NODE_FORKS_READ, CoreScopes.NODE_BASE_READ]
    required_write_scopes = [CoreScopes.NODE_FORKS_WRITE]

    serializer_class = NodeForksSerializer
    view_category = 'nodes'
    view_name = 'node-forks'

    ordering = ('-forked_date',)

    # overrides ListCreateAPIView
    def get_queryset(self):
        all_forks = (
            self.get_node().forks
            .annotate(region=F('addons_osfstorage_node_settings__region___id'))
            .exclude(region=None)
            .exclude(type='osf.registration')
            .exclude(is_deleted=True)
            .order_by('-forked_date')
        )
        auth = get_user_auth(self.request)

        node_pks = [node.pk for node in all_forks if node.can_view(auth)]
        return AbstractNode.objects.filter(pk__in=node_pks)

    # overrides ListCreateAPIView
    def perform_create(self, serializer):
        user = get_user_auth(self.request).user
        node = self.get_node()
        try:
            fork = serializer.save(node=node)
        except Exception as exc:
            mails.send_mail(user.email, mails.FORK_FAILED, title=node.title, guid=node._id, can_change_preferences=False)
            raise exc
        else:
            mails.send_mail(user.email, mails.FORK_COMPLETED, title=node.title, guid=fork._id, can_change_preferences=False)


class NodeLinkedByNodesList(JSONAPIBaseView, generics.ListAPIView, NodeMixin):
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        ContributorOrPublic,
        ExcludeWithdrawals,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.NODE_BASE_READ]
    required_write_scopes = [CoreScopes.NULL]

    view_category = 'nodes'
    view_name = 'node-linked-by-nodes'
    ordering = ('-modified',)

    serializer_class = NodeSerializer

    def get_queryset(self):
        node = self.get_node()
        auth = get_user_auth(self.request)
        node_relation_subquery = node._parents.filter(is_node_link=True).values_list('parent', flat=True)
        return Node.objects.filter(id__in=Subquery(node_relation_subquery), is_deleted=False).can_view(user=auth.user, private_link=auth.private_link)


class NodeLinkedByRegistrationsList(JSONAPIBaseView, generics.ListAPIView, NodeMixin):
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        ContributorOrPublic,
        ExcludeWithdrawals,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.NODE_BASE_READ]
    required_write_scopes = [CoreScopes.NULL]

    view_category = 'nodes'
    view_name = 'node-linked-by-registrations'
    ordering = ('-modified',)

    serializer_class = RegistrationSerializer

    def get_queryset(self):
        node = self.get_node()
        auth = get_user_auth(self.request)
        node_relation_subquery = node._parents.filter(is_node_link=True).values_list('parent', flat=True)
        return Registration.objects.filter(id__in=Subquery(node_relation_subquery), retraction__isnull=True).can_view(user=auth.user, private_link=auth.private_link)


class NodeFilesList(JSONAPIBaseView, generics.ListAPIView, WaterButlerMixin, ListFilterMixin, NodeMixin):
    """The documentation for this endpoint can be found [here](https://developer.osf.io/#operation/nodes_files_list).

    """
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.PermissionWithGetter(ContributorOrPublic, 'target'),
        base_permissions.PermissionWithGetter(ReadOnlyIfRegistration, 'target'),
        base_permissions.TokenHasScope,
        ExcludeWithdrawals,
    )

    ordering = ('_materialized_path',)  # default ordering

    required_read_scopes = [CoreScopes.NODE_FILE_READ]
    required_write_scopes = [CoreScopes.NODE_FILE_WRITE]

    throttle_classes = (FilesBurstRateThrottle, FilesRateThrottle, )

    view_category = 'nodes'
    view_name = 'node-files'

    @property
    def serializer_class(self):
        if self.kwargs[self.provider_lookup_url_kwarg] == 'osfstorage':
            return OsfStorageFileSerializer
        return FileSerializer

    # overrides FilterMixin
    def postprocess_query_param(self, key, field_name, operation):
        # tag queries will usually be on Tag.name,
        # ?filter[tags]=foo should be translated to MQ('tags__name', 'eq', 'foo')
        # But queries on lists should be tags, e.g.
        # ?filter[tags]=foo,bar should be translated to MQ('tags', 'isnull', True)
        # ?filter[tags]=[] should be translated to MQ('tags', 'isnull', True)
        if field_name == 'tags':
            if operation['value'] not in (list(), tuple()):
                operation['source_field_name'] = 'tags__name'
                operation['op'] = 'iexact'
        if field_name == 'path':
            operation['source_field_name'] = '_path'
        # NOTE: This is potentially fragile, if we ever add filtering on provider
        # we're going to have to get a bit tricky. get_default_queryset should ramain filtering on BaseFileNode, for now
        if field_name == 'kind':
            if operation['value'].lower() == 'folder':
                kind = Folder
            else:
                # Default to File, should probably raise an exception in the future
                kind = File  # Default to file

            operation['source_field_name'] = 'type'
            operation['op'] = 'in'
            operation['value'] = [
                sub._typedmodels_type
                for sub in kind.__subclasses__()
                if hasattr(sub, '_typedmodels_type')
            ]

    def get_default_queryset(self):
        files_list = self.fetch_from_waterbutler()

        if isinstance(files_list, list):
            provider = self.kwargs[self.provider_lookup_url_kwarg]
            # Resolve to a provider-specific subclass, so that
            # trashed file nodes are filtered out automatically
            ConcreteFileNode = BaseFileNode.resolve_class(provider, BaseFileNode.ANY)
            file_ids = [f.id for f in self.bulk_get_file_nodes_from_wb_resp(files_list)]
            return ConcreteFileNode.objects.filter(id__in=file_ids)

        if isinstance(files_list, list) or not isinstance(files_list, Folder):
            # We should not have gotten a file here
            raise NotFound

        sub_qs = OsfStorageFolder.objects.filter(_children=OuterRef('pk'), pk=files_list.pk)
        return files_list.children.annotate(folder=Exists(sub_qs)).filter(folder=True).prefetch_related('versions', 'tags', 'guids')

    # overrides ListAPIView
    def get_queryset(self):
        path = self.kwargs[self.path_lookup_url_kwarg]
        # query param info when used on a folder gives that folder's metadata instead of the metadata of it's children
        if 'info' in self.request.query_params and path.endswith('/'):
            fobj = self.fetch_from_waterbutler()

            if isinstance(fobj, list):
                node = self.get_node(check_object_permissions=False)
                base_class = BaseFileNode.resolve_class(self.kwargs[self.provider_lookup_url_kwarg], BaseFileNode.FOLDER)
                return base_class.objects.filter(
                    target_object_id=node.id, target_content_type=ContentType.objects.get_for_model(node), _path=path,
                )
            elif isinstance(fobj, OsfStorageFolder):
                return BaseFileNode.objects.filter(id=fobj.id)
            else:
                raise NotFound
        else:
            return self.get_queryset_from_request().distinct()


class NodeFileDetail(JSONAPIBaseView, generics.RetrieveAPIView, WaterButlerMixin, NodeMixin):
    """The documentation for this endpoint can be found [here](https://developer.osf.io/#operation/nodes_files_read).

    """
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.PermissionWithGetter(ContributorOrPublic, 'target'),
        base_permissions.PermissionWithGetter(ReadOnlyIfRegistration, 'target'),
        base_permissions.TokenHasScope,
        ExcludeWithdrawals,
    )

    serializer_class = FileSerializer

    required_read_scopes = [CoreScopes.NODE_FILE_READ]
    required_write_scopes = [CoreScopes.NODE_FILE_WRITE]
    view_category = 'nodes'
    view_name = 'node-file-detail'

    def get_object(self):
        fobj = self.fetch_from_waterbutler()
        if isinstance(fobj, dict):
            # if dict it is a wb response, not file object yet
            return self.get_file_node_from_wb_resp(fobj)

        if isinstance(fobj, list) or not isinstance(fobj, File):
            # We should not have gotten a folder here
            raise NotFound

        return fobj


class NodeGroupsBase(JSONAPIBaseView, NodeMixin, OSFGroupMixin):
    model_class = OSFGroup

    required_read_scopes = [CoreScopes.NODE_OSF_GROUPS_READ]
    required_write_scopes = [CoreScopes.NODE_OSF_GROUPS_WRITE]
    view_category = 'nodes'


class NodeGroupsList(NodeGroupsBase, generics.ListCreateAPIView, ListFilterMixin):
    """ The documentation for this endpoint can be found [here](https://developer.osf.io/#operation/nodes_groups_list)

    """
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        AdminOrPublic,
        base_permissions.TokenHasScope,
    )

    serializer_class = NodeGroupsSerializer
    view_name = 'node-groups'

    @require_flag(OSF_GROUPS)
    def get_default_queryset(self):
        return self.get_node().osf_groups

    def get_queryset(self):
        return self.get_queryset_from_request()

    # overrides FilterMixin
    def build_query_from_field(self, field_name, operation):
        if field_name == 'permission':
            node = self.get_node()
            try:
                groups_with_perm_ids = node.get_osf_groups_with_perms(operation['value']).values_list('id', flat=True)
            except ValueError:
                raise ValidationError('{} is not a filterable permission.'.format(operation['value']))
            return Q(id__in=groups_with_perm_ids)

        return super(NodeGroupsList, self).build_query_from_field(field_name, operation)

    # overrides ListCreateAPIView
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return NodeGroupsCreateSerializer
        else:
            return NodeGroupsSerializer

    # overrides ListCreateAPIView
    def get_serializer_context(self):
        """
        Extra context for NodeGroupsSerializer
        """
        context = super(NodeGroupsList, self).get_serializer_context()
        context['node'] = self.get_node(check_object_permissions=False)
        return context

    @require_flag(OSF_GROUPS)
    def perform_create(self, serializer):
        return super(NodeGroupsList, self).perform_create(serializer)


class NodeGroupsDetail(NodeGroupsBase, generics.RetrieveUpdateDestroyAPIView):
    """ The documentation for this endpoint can be found [here](https://developer.osf.io/#operation/nodes_groups_read)

    """
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        NodeGroupDetailPermissions,
        base_permissions.TokenHasScope,
    )

    serializer_class = NodeGroupsDetailSerializer

    view_name = 'node-group-detail'

    # Overrides RetrieveUpdateDestroyAPIView
    @require_flag(OSF_GROUPS)
    def get_object(self):
        node = self.get_node(check_object_permissions=False)
        # Node permissions checked when group is loaded
        group = self.get_osf_group(self.kwargs.get('group_id'))
        if not group.get_permission_to_node(node):
            raise NotFound('Group {} does not have permissions to node {}.'.format(group._id, node._id))
        return group

    # Overrides RetrieveUpdateDestroyAPIView
    @require_flag(OSF_GROUPS)
    def perform_destroy(self, instance):
        node = self.get_node(check_object_permissions=False)
        auth = get_user_auth(self.request)
        try:
            node.remove_osf_group(instance, auth)
        except PermissionsError:
            raise PermissionDenied('Not authorized to remove this group.')

    # Overrides RetrieveUpdateDestroyAPIView
    def get_serializer_context(self):
        """
        Extra context for NodeGroupsSerializer
        """
        context = super(NodeGroupsDetail, self).get_serializer_context()
        context['node'] = self.get_node(check_object_permissions=False)
        return context


class NodeAddonList(JSONAPIBaseView, generics.ListAPIView, ListFilterMixin, NodeMixin, AddonSettingsMixin):
    """The documentation for this endpoint can be found [here](https://developer.osf.io/#operation/nodes_addons_list).

    """

    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        ContributorOrPublic,
        ExcludeWithdrawals,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.NODE_ADDON_READ]
    required_write_scopes = [CoreScopes.NULL]

    serializer_class = NodeAddonSettingsSerializer
    view_category = 'nodes'
    view_name = 'node-addons'

    ordering = ('-id',)

    def get_default_queryset(self):
        qs = []
        for addon in ADDONS_OAUTH:
            obj = self.get_addon_settings(provider=addon, fail_if_absent=False, check_object_permissions=False)
            if obj:
                qs.append(obj)
        sorted(qs, key=lambda addon: addon.id, reverse=True)
        return qs

    get_queryset = get_default_queryset


class NodeAddonDetail(JSONAPIBaseView, generics.RetrieveUpdateDestroyAPIView, generics.CreateAPIView, NodeMixin, AddonSettingsMixin):
    """The documentation for this endpoint can be found [here](https://developer.osf.io/#operation/nodes_addon_read).
    """

    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        ContributorOrPublic,
        ExcludeWithdrawals,
        ReadOnlyIfRegistration,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.NODE_ADDON_READ]
    required_write_scopes = [CoreScopes.NODE_ADDON_WRITE]

    serializer_class = NodeAddonSettingsSerializer
    view_category = 'nodes'
    view_name = 'node-addon-detail'

    def get_object(self):
        return self.get_addon_settings(check_object_permissions=False)

    def perform_create(self, serializer):
        addon = self.kwargs['provider']
        if addon not in ADDONS_OAUTH:
            raise NotFound('Requested addon unavailable')

        node = self.get_node()
        if node.has_addon(addon):
            raise InvalidModelValueError(
                detail='Add-on {} already enabled for node {}'.format(addon, node._id),
            )

        return super(NodeAddonDetail, self).perform_create(serializer)

    def perform_destroy(self, instance):
        addon = instance.config.short_name
        node = self.get_node()
        if not node.has_addon(instance.config.short_name):
            raise NotFound('Node {} does not have add-on {}'.format(node._id, addon))

        node.delete_addon(addon, auth=get_user_auth(self.request))

    def get_serializer_class(self):
        """
        Use NodeDetailSerializer which requires 'id'
        """
        if 'provider' in self.kwargs and self.kwargs['provider'] == 'forward':
            return ForwardNodeAddonSettingsSerializer
        else:
            return NodeAddonSettingsSerializer


class NodeAddonFolderList(JSONAPIBaseView, generics.ListAPIView, NodeMixin, AddonSettingsMixin):
    """The documentation for this endpoint can be found [here](https://developer.osf.io/#operation/nodes_addons_folders_list).
    """
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        ContributorOrPublic,
        ExcludeWithdrawals,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.NODE_ADDON_READ, CoreScopes.NODE_FILE_READ]
    required_write_scopes = [CoreScopes.NULL]

    pagination_class = MaxSizePagination
    serializer_class = NodeAddonFolderSerializer
    view_category = 'nodes'
    view_name = 'node-addon-folders'

    def get_queryset(self):
        # TODO: [OSF-6120] refactor this/NS models to be generalizable
        node_addon = self.get_addon_settings()
        if not node_addon.has_auth:
            raise JSONAPIException(
                detail='This addon is enabled but an account has not been imported from your user settings',
                meta={'link': '{}users/me/addons/{}/accounts/'.format(API_BASE, node_addon.config.short_name)},
            )

        path = self.request.query_params.get('path')
        folder_id = self.request.query_params.get('id')

        if not hasattr(node_addon, 'get_folders'):
            raise EndpointNotImplementedError('Endpoint not yet implemented for this addon')

        #  Convert v1 errors to v2 as much as possible.
        try:
            return node_addon.get_folders(path=path, folder_id=folder_id)
        except InvalidAuthError:
            raise NotAuthenticated('This add-on could not be authenticated.')
        except HTTPError as exc:
            raise HTTP_CODE_MAP.get(exc.code, exc)


class NodeStorageProvider(object):

    def __init__(self, node, provider_name, storage_addon=None):
        self.path = '/'
        self.node = node
        self.kind = 'folder'
        self.name = provider_name
        self.provider = provider_name
        self.node_id = node._id
        self.pk = node._id
        self.id = node.id
        self.root_folder = storage_addon.root_node if storage_addon else None

    @property
    def target(self):
        return self.node

class NodeStorageProvidersList(JSONAPIBaseView, generics.ListAPIView, NodeMixin):
    """The documentation for this endpoint can be found [here](https://developer.osf.io/#operation/nodes_providers_list).
    """
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        ContributorOrPublic,
        ExcludeWithdrawals,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.NODE_FILE_READ]
    required_write_scopes = [CoreScopes.NODE_FILE_WRITE]

    serializer_class = NodeStorageProviderSerializer
    view_category = 'nodes'
    view_name = 'node-storage-providers'

    ordering = ('-id',)

    def get_provider_item(self, storage_addon):
        return NodeStorageProvider(self.get_node(), storage_addon.config.short_name, storage_addon)

    def get_queryset(self):
        return [
            self.get_provider_item(addon)
            for addon
            in self.get_node().get_addons()
            if addon.config.has_hgrid_files
            and addon.configured
        ]

class NodeStorageProviderDetail(JSONAPIBaseView, generics.RetrieveAPIView, NodeMixin):
    """The documentation for this endpoint can be found [here](https://developer.osf.io/#operation/nodes_providers_read).
    """
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        ContributorOrPublic,
        ExcludeWithdrawals,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.NODE_FILE_READ]
    required_write_scopes = [CoreScopes.NODE_FILE_WRITE]

    serializer_class = NodeStorageProviderSerializer
    view_category = 'nodes'
    view_name = 'node-storage-provider-detail'

    def get_object(self):
        return NodeStorageProvider(self.get_node(), self.kwargs['provider'])


class NodeLogList(JSONAPIBaseView, generics.ListAPIView, NodeMixin, ListFilterMixin):
    """The documentation for this endpoint can be found [here](https://developer.osf.io/#operation/nodes_logs_list).
    """

    serializer_class = NodeLogSerializer
    view_category = 'nodes'
    view_name = 'node-logs'

    required_read_scopes = [CoreScopes.NODE_LOG_READ]
    required_write_scopes = [CoreScopes.NULL]

    log_lookup_url_kwarg = 'node_id'

    ordering = ('-date', )

    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        ContributorOrPublic,
        base_permissions.TokenHasScope,
        ExcludeWithdrawals,
    )

    def get_default_queryset(self):
        auth = get_user_auth(self.request)
        return self.get_node().get_logs_queryset(auth)

    def get_queryset(self):
        return self.get_queryset_from_request().include(
            'node__guids', 'user__guids', 'original_node__guids', limit_includes=10,
        )


class NodeCommentsList(JSONAPIBaseView, generics.ListCreateAPIView, ListFilterMixin, NodeMixin):
    """The documentation for this endpoint can be found [here](https://developer.osf.io/#operation/nodes_comments_list).
    """
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        CanCommentOrPublic,
        base_permissions.TokenHasScope,
        ExcludeWithdrawals,
    )

    required_read_scopes = [CoreScopes.NODE_COMMENTS_READ]
    required_write_scopes = [CoreScopes.NODE_COMMENTS_WRITE]

    pagination_class = CommentPagination
    serializer_class = NodeCommentSerializer
    view_category = 'nodes'
    view_name = 'node-comments'

    ordering = ('-created', )  # default ordering

    def get_default_queryset(self):
        return Comment.objects.filter(node=self.get_node(), root_target__isnull=False)

    # Hook to make filtering on 'target' work
    def postprocess_query_param(self, key, field_name, operation):
        if field_name == 'target':
            operation['value'] = Guid.load(operation['value'])

    def get_queryset(self):
        return self.get_queryset_from_request()

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return CommentCreateSerializer
        else:
            return NodeCommentSerializer

    # overrides ListCreateAPIView
    def get_parser_context(self, http_request):
        """
        Tells parser that we are creating a relationship
        """
        res = super(NodeCommentsList, self).get_parser_context(http_request)
        res['is_relationship'] = True
        return res

    def perform_create(self, serializer):
        node = self.get_node()
        serializer.validated_data['user'] = self.request.user
        serializer.validated_data['node'] = node
        serializer.save()


class NodeInstitutionsList(JSONAPIBaseView, generics.ListAPIView, ListFilterMixin, NodeMixin):
    """The documentation for this endpoint can be found [here](https://developer.osf.io/#operation/nodes_institutions_list).
    """
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
        AdminOrPublic,
        ReadOnlyIfWithdrawn,
    )

    required_read_scopes = [CoreScopes.NODE_BASE_READ, CoreScopes.INSTITUTION_READ]
    required_write_scopes = [CoreScopes.NULL]
    serializer_class = InstitutionSerializer

    model = Institution
    view_category = 'nodes'
    view_name = 'node-institutions'

    ordering = ('-id',)

    def get_resource(self):
        return self.get_node()

    def get_queryset(self):
        resource = self.get_resource()
        return resource.affiliated_institutions.all() or []


class NodeInstitutionsRelationship(JSONAPIBaseView, generics.RetrieveUpdateDestroyAPIView, generics.CreateAPIView, NodeMixin):
    """ Relationship Endpoint for Node -> Institutions Relationship

    Used to set, remove, update and retrieve the affiliated_institutions of a node to an institution

    ##Actions

    ###Create

        Method:        POST
        URL:           /links/self
        Query Params:  <none>
        Body (JSON):   {
                         "data": [{
                           "type": "institutions",   # required
                           "id": <institution_id>   # required
                         }]
                       }
        Success:       201

        This requires write permissions on the node and for the user making the request to
        have the institutions in the payload as affiliated in their account.

    ###Update

        Method:        PUT || PATCH
        URL:           /links/self
        Query Params:  <none>
        Body (JSON):   {
                         "data": [{
                           "type": "institutions",   # required
                           "id": <institution_id>   # required
                         }]
                       }
        Success:       200

        This requires write permissions on the node and for the user making the request to
        have the institutions in the payload as affiliated in their account. This will delete
        all institutions not listed, meaning a data: [] payload does the same as a DELETE with all
        the institutions.

    ###Destroy

        Method:        DELETE
        URL:           /links/self
        Query Params:  <none>
        Body (JSON):   {
                         "data": [{
                           "type": "institutions",   # required
                           "id": <institution_id>   # required
                         }]
                       }
        Success:       204

        This requires write permissions in the node. If the user has admin permissions, the institution in the payload does
        not need to be affiliated in their account.
    """
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
        WriteOrPublicForRelationshipInstitutions,
    )
    required_read_scopes = [CoreScopes.NODE_BASE_READ]
    required_write_scopes = [CoreScopes.NODE_BASE_WRITE]
    serializer_class = NodeInstitutionsRelationshipSerializer
    parser_classes = (JSONAPIRelationshipParser, JSONAPIRelationshipParserForRegularJSON, )

    view_category = 'nodes'
    view_name = 'node-relationships-institutions'

    def get_resource(self):
        return self.get_node(check_object_permissions=False)

    def get_object(self):
        node = self.get_resource()
        obj = {
            'data': node.affiliated_institutions.all(),
            'self': node,
        }
        self.check_object_permissions(self.request, obj)
        return obj

    def perform_destroy(self, instance):
        data = self.request.data['data']
        user = self.request.user
        current_insts = {inst._id: inst for inst in instance['data']}
        node = instance['self']

        for val in data:
            if val['id'] in current_insts:
                if not user.is_affiliated_with_institution(current_insts[val['id']]) and not node.has_permission(user, ADMIN):
                    raise PermissionDenied
                node.remove_affiliated_institution(inst=current_insts[val['id']], user=user)
        node.save()

    def create(self, *args, **kwargs):
        try:
            ret = super(NodeInstitutionsRelationship, self).create(*args, **kwargs)
        except RelationshipPostMakesNoChanges:
            return Response(status=HTTP_204_NO_CONTENT)
        return ret


class NodeStorage(JSONAPIBaseView, generics.RetrieveAPIView, NodeMixin):
    """The documentation for this endpoint should be found [here](https://developer.osf.io/#operation/node_storage)
    """
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
        WriteAdmin,
    )

    required_read_scopes = [CoreScopes.NODE_CONTRIBUTORS_WRITE]
    required_write_scopes = [CoreScopes.NULL]

    view_category = 'nodes'
    view_name = 'node-storage'

    serializer_class = NodeStorageSerializer

    def get_object(self):
        return self.get_node()

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        if instance.storage_limit_status is settings.StorageLimits.NOT_CALCULATED:
            return Response(serializer.data, status=HTTP_202_ACCEPTED)
        else:
            return Response(serializer.data)


class NodeSubjectsList(BaseResourceSubjectsList, NodeMixin):
    """The documentation for this endpoint can be found [here](https://developer.osf.io/#operation/nodes_subjects_list).
    """
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
        ContributorOrPublic,
        ExcludeWithdrawals,
    )

    required_read_scopes = [CoreScopes.NODE_BASE_READ]

    view_category = 'nodes'
    view_name = 'node-subjects'

    def get_resource(self):
        return self.get_node()


class NodeSubjectsRelationship(SubjectRelationshipBaseView, NodeMixin):
    """The documentation for this endpoint can be found [here](https://developer.osf.io/#operation/node_subjects_relationship).
    """
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
        ContributorOrPublic,
        ExcludeWithdrawals,
    )

    required_read_scopes = [CoreScopes.NODE_BASE_READ]
    required_write_scopes = [CoreScopes.NODE_BASE_WRITE]

    view_category = 'nodes'
    view_name = 'node-relationships-subjects'

    ordering = ('-id',)

    def get_resource(self, check_object_permissions=True):
        return self.get_node(check_object_permissions=check_object_permissions)


class NodeWikiList(JSONAPIBaseView, generics.ListCreateAPIView, NodeMixin, ListFilterMixin):
    """The documentation for this endpoint can be found [here](https://developer.osf.io/#operation/nodes_wikis_list).
    """

    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
        ContributorOrPublic,
        ExcludeWithdrawals,
    )

    required_read_scopes = [CoreScopes.WIKI_BASE_READ]
    required_write_scopes = [CoreScopes.WIKI_BASE_WRITE]
    serializer_class = NodeWikiSerializer

    view_category = 'nodes'
    view_name = 'node-wikis'

    ordering = ('-modified', )  # default ordering

    def get_default_queryset(self):
        node = self.get_node()
        if node.addons_wiki_node_settings.deleted:
            raise NotFound(detail='The wiki for this node has been disabled.')
        return node.wikis.filter(deleted__isnull=True)

    def get_queryset(self):
        return self.get_queryset_from_request()

    def perform_create(self, serializer):
        return serializer.save(node=self.get_node())


class NodeLinkedNodesRelationship(LinkedNodesRelationship, NodeMixin):
    """ Relationship Endpoint for Nodes -> Linked Node relationships

    Used to set, remove, update and retrieve the ids of the linked nodes attached to this collection. For each id, there
    exists a node link that contains that node.

    ##Actions

    ###Create

        Method:        POST
        URL:           /links/self
        Query Params:  <none>
        Body (JSON):   {
                         "data": [{
                           "type": "nodes",   # required
                           "id": <node_id>   # required
                         }]
                       }
        Success:       201

    This requires both edit permission on the collection, and for the user that is
    making the request to be able to read the nodes requested. Data can be contain any number of
    node identifiers. This will create a node_link for all node_ids in the request that
    do not currently have a corresponding node_link in this collection.

    ###Update

        Method:        PUT || PATCH
        URL:           /links/self
        Query Params:  <none>
        Body (JSON):   {
                         "data": [{
                           "type": "nodes",   # required
                           "id": <node_id>   # required
                         }]
                       }
        Success:       200

    This requires both edit permission on the collection, and for the user that is
    making the request to be able to read the nodes requested. Data can be contain any number of
    node identifiers. This will replace the contents of the node_links for this collection with
    the contents of the request. It will delete all node links that don't have a node_id in the data
    array, create node links for the node_ids that don't currently have a node id, and do nothing
    for node_ids that already have a corresponding node_link. This means a update request with
    {"data": []} will remove all node_links in this collection

    ###Destroy

        Method:        DELETE
        URL:           /links/self
        Query Params:  <none>
        Body (JSON):   {
                         "data": [{
                           "type": "nodes",   # required
                           "id": <node_id>   # required
                         }]
                       }
        Success:       204

    This requires edit permission on the node. This will delete any node_links that have a
    corresponding node_id in the request.
    """

    view_category = 'nodes'
    view_name = 'node-pointer-relationship'


class LinkedNodesList(BaseLinkedList, NodeMixin):
    """The documentation for this endpoint can be found [here](https://developer.osf.io/#operation/nodes_linked_nodes_list).
    """
    serializer_class = NodeSerializer
    view_category = 'nodes'
    view_name = 'linked-nodes'

    def get_queryset(self):
        queryset = super(LinkedNodesList, self).get_queryset()
        return queryset.exclude(type='osf.registration')

    # overrides APIView
    def get_parser_context(self, http_request):
        """
        Tells parser that we are creating a relationship
        """
        res = super(LinkedNodesList, self).get_parser_context(http_request)
        res['is_relationship'] = True
        return res


class NodeLinkedRegistrationsRelationship(LinkedRegistrationsRelationship, NodeMixin):
    """ Relationship Endpoint for Node -> Linked Registration relationships

    Used to set, remove, update and retrieve the ids of the linked registrations attached to this node. For each id, there
    exists a node link that contains that node.

    ##Actions

    ###Create

        Method:        POST
        URL:           /links/self
        Query Params:  <none>
        Body (JSON):   {
                         "data": [{
                           "type": "registrations",   # required
                           "id": <node_id>   # required
                         }]
                       }
        Success:       201

    This requires both edit permission on the node, and for the user that is
    making the request to be able to read the registrations requested. Data can contain any number of
    node identifiers. This will create a node_link for all node_ids in the request that
    do not currently have a corresponding node_link in this node.

    ###Update

        Method:        PUT || PATCH
        URL:           /links/self
        Query Params:  <none>
        Body (JSON):   {
                         "data": [{
                           "type": "registrations",   # required
                           "id": <node_id>   # required
                         }]
                       }
        Success:       200

    This requires both edit permission on the node, and for the user that is
    making the request to be able to read the registrations requested. Data can contain any number of
    node identifiers. This will replace the contents of the node_links for this node with
    the contents of the request. It will delete all node links that don't have a node_id in the data
    array, create node links for the node_ids that don't currently have a node id, and do nothing
    for node_ids that already have a corresponding node_link. This means a update request with
    {"data": []} will remove all node_links in this node.

    ###Destroy

        Method:        DELETE
        URL:           /links/self
        Query Params:  <none>
        Body (JSON):   {
                         "data": [{
                           "type": "registrations",   # required
                           "id": <node_id>   # required
                         }]
                       }
        Success:       204

    This requires edit permission on the node. This will delete any node_links that have a
    corresponding node_id in the request.
    """

    view_category = 'nodes'
    view_name = 'node-registration-pointer-relationship'


class NodeLinkedRegistrationsList(BaseLinkedList, NodeMixin):
    """List of registrations linked to this node. *Read-only*.

    Linked registrations are the registration nodes pointed to by node links.

    <!--- Copied Spiel from RegistrationDetail -->
    Registrations are read-only snapshots of a project. This view shows details about the given registration.

    Each resource contains the full representation of the registration, meaning additional requests to an individual
    registration's detail view are not necessary. A withdrawn registration will display a limited subset of information,
    namely, title, description, created, registration, withdrawn, date_registered, withdrawal_justification, and
    registration supplement. All other fields will be displayed as null. Additionally, the only relationships permitted
    to be accessed for a withdrawn registration are the contributors - other relationships will return a 403.

    ##Linked Registration Attributes

    <!--- Copied Attributes from RegistrationDetail -->

    Registrations have the "registrations" `type`.

        name                            type               description
        =======================================================================================================
        title                           string             title of the registered project or component
        description                     string             description of the registered node
        category                        string             bode category, must be one of the allowed values
        created                         iso8601 timestamp  timestamp that the node was created
        modified                        iso8601 timestamp  timestamp when the node was last updated
        tags                            array of strings   list of tags that describe the registered node
        current_user_can_comment        boolean            Whether the current user is allowed to post comments
        current_user_permissions        array of strings   list of strings representing the permissions for the current user on this node
        fork                            boolean            is this project a fork?
        registration                    boolean            has this project been registered? (always true - may be deprecated in future versions)
        collection                      boolean            is this registered node a collection? (always false - may be deprecated in future versions)
        node_license                    object             details of the license applied to the node
        year                            string             date range of the license
        copyright_holders               array of strings   holders of the applied license
        public                          boolean            has this registration been made publicly-visible?
        withdrawn                       boolean            has this registration been withdrawn?
        date_registered                 iso8601 timestamp  timestamp that the registration was created
        embargo_end_date                iso8601 timestamp  when the embargo on this registration will be lifted (if applicable)
        withdrawal_justification        string             reasons for withdrawing the registration
        pending_withdrawal              boolean            is this registration pending withdrawal?
        pending_withdrawal_approval     boolean            is this registration pending approval?
        pending_embargo_approval        boolean            is the associated Embargo awaiting approval by project admins?
        registered_meta                 dictionary         registration supplementary information
        registration_supplement         string             registration template

    ##Links

    See the [JSON-API spec regarding pagination](http://jsonapi.org/format/1.0/#fetching-pagination).

    ##Query Params

    + `page=<Int>` -- page number of results to view, default 1

    + `filter[<fieldname>]=<Str>` -- fields and values to filter the search results on.

    Nodes may be filtered by their `title`, `category`, `description`, `public`, `registration`, or `tags`.  `title`,
    `description`, and `category` are string fields and will be filtered using simple substring matching.  `public` and
    `registration` are booleans, and can be filtered using truthy values, such as `true`, `false`, `0`, or `1`.  Note
    that quoting `true` or `false` in the query will cause the match to fail regardless.  `tags` is an array of simple strings.

    #This Request/Response
    """
    serializer_class = RegistrationSerializer
    view_category = 'nodes'
    view_name = 'linked-registrations'

    def get_queryset(self):
        return super(NodeLinkedRegistrationsList, self).get_queryset().filter(type='osf.registration')

    # overrides APIView
    def get_parser_context(self, http_request):
        """
        Tells parser that we are creating a relationship
        """
        res = super(NodeLinkedRegistrationsList, self).get_parser_context(http_request)
        res['is_relationship'] = True
        return res


class NodeViewOnlyLinksList(JSONAPIBaseView, generics.ListCreateAPIView, ListFilterMixin, NodeMixin):
    """The documentation for this endpoint can be found [here](https://developer.osf.io/#operation/nodes_view_only_links_list).
    """
    permission_classes = (
        IsAdmin,
        base_permissions.TokenHasScope,
        drf_permissions.IsAuthenticatedOrReadOnly,
    )

    required_read_scopes = [CoreScopes.NODE_VIEW_ONLY_LINKS_READ]
    required_write_scopes = [CoreScopes.NODE_VIEW_ONLY_LINKS_WRITE]

    serializer_class = NodeViewOnlyLinkSerializer

    view_category = 'nodes'
    view_name = 'node-view-only-links'

    ordering = ('-created',)

    def get_default_queryset(self):
        return self.get_node().private_links.filter(is_deleted=False)

    def get_queryset(self):
        return self.get_queryset_from_request()


class NodeViewOnlyLinkDetail(JSONAPIBaseView, generics.RetrieveUpdateDestroyAPIView, NodeMixin):
    """The documentation for this endpoint can be found [here](https://developer.osf.io/#operation/nodes_view_only_links_read).
    """

    permission_classes = (
        IsAdmin,
        base_permissions.TokenHasScope,
        drf_permissions.IsAuthenticatedOrReadOnly,
    )

    required_read_scopes = [CoreScopes.NODE_VIEW_ONLY_LINKS_READ]
    required_write_scopes = [CoreScopes.NODE_VIEW_ONLY_LINKS_WRITE]

    serializer_class = NodeViewOnlyLinkSerializer

    view_category = 'nodes'
    view_name = 'node-view-only-link-detail'

    def get_serializer_class(self):
        if self.request.method == 'PUT' or self.request.method == 'PATCH':
            return NodeViewOnlyLinkUpdateSerializer
        return NodeViewOnlyLinkSerializer

    def get_object(self):
        try:
            return self.get_node().private_links.get(_id=self.kwargs['link_id'], is_deleted=False)
        except PrivateLink.DoesNotExist:
            raise NotFound

    def perform_destroy(self, link):
        assert isinstance(link, PrivateLink), 'link must be a PrivateLink'
        link.is_deleted = True
        link.deleted = timezone.now()
        link.save()
        # FIXME: Doesn't work because instance isn't JSON-serializable
        # enqueue_postcommit_task(ban_url, (self.get_node(),), {}, celery=False, once_per_request=True)

class NodeIdentifierList(NodeMixin, IdentifierList):
    """The documentation for this endpoint can be found [here](https://developer.osf.io/#operation/nodes_identifiers_list).
    """

    serializer_class = NodeIdentifierSerializer
    node_lookup_url_kwarg = 'node_id'

    view_category = 'nodes'
    view_name = 'identifier-list'

    # overrides IdentifierList
    def get_object(self, check_object_permissions=True):
        return self.get_node(check_object_permissions=check_object_permissions)

    def get_node(self, check_object_permissions=True):
        node = get_object_or_error(
            Node,
            self.kwargs[self.node_lookup_url_kwarg],
            self.request,
            display_name='node',
        )
        # Nodes that are folders/collections are treated as a separate resource, so if the client
        # requests a collection through a node endpoint, we return a 404
        if node.is_collection:
            raise NotFound
        # May raise a permission denied
        if check_object_permissions:
            self.check_object_permissions(self.request, node)
        return node


class NodePreprintsList(JSONAPIBaseView, generics.ListAPIView, NodeMixin, PreprintFilterMixin):
    """The documentation for this endpoint can be found [here](https://developer.osf.io/#operation/nodes_preprints_list).
    """
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
        ContributorOrPublic,
    )
    parser_classes = (JSONAPIMultipleRelationshipsParser, JSONAPIMultipleRelationshipsParserForRegularJSON,)

    required_read_scopes = [CoreScopes.NODE_PREPRINTS_READ]
    required_write_scopes = [CoreScopes.NODE_PREPRINTS_WRITE]

    serializer_class = PreprintSerializer

    view_category = 'nodes'
    view_name = 'node-preprints'

    ordering = ('-modified',)

    def get_default_queryset(self):
        auth = get_user_auth(self.request)
        auth_user = getattr(auth, 'user', None)
        node = self.get_node()
        # Permissions on the node are handled by the permissions_classes
        # Permissions on the list objects are handled by the query
        return self.preprints_queryset(node.preprints.all(), auth_user)

    def get_queryset(self):
        return self.get_queryset_from_request()


class NodeRequestListCreate(JSONAPIBaseView, generics.ListCreateAPIView, ListFilterMixin, NodeRequestMixin):
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
        NodeRequestPermission,
    )

    required_read_scopes = [CoreScopes.NODE_REQUESTS_READ]
    required_write_scopes = [CoreScopes.NODE_REQUESTS_WRITE]

    parser_classes = (JSONAPIMultipleRelationshipsParser, JSONAPIMultipleRelationshipsParserForRegularJSON,)

    serializer_class = NodeRequestSerializer

    view_category = 'node-requests'
    view_name = 'node-request-list'

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return NodeRequestCreateSerializer
        else:
            return NodeRequestSerializer

    def get_default_queryset(self):
        return self.get_target().requests.all()

    def get_queryset(self):
        return self.get_queryset_from_request()


class NodeSettings(JSONAPIBaseView, generics.RetrieveUpdateAPIView, NodeMixin):
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
        IsContributorOrGroupMember,
    )

    required_read_scopes = [CoreScopes.NODE_SETTINGS_READ]
    required_write_scopes = [CoreScopes.NODE_SETTINGS_WRITE]

    serializer_class = NodeSettingsSerializer

    view_category = 'nodes'
    view_name = 'node-settings'

    # overrides RetrieveUpdateAPIView
    def get_object(self):
        return self.get_node()

    def get_serializer_class(self):
        if self.request.method == 'PUT' or self.request.method == 'PATCH':
            return NodeSettingsUpdateSerializer
        return NodeSettingsSerializer

    def get_serializer_context(self):
        """
        Extra context for NodeSettingsSerializer - this will prevent loading
        addons multiple times in SerializerMethodFields
        """
        context = super(NodeSettings, self).get_serializer_context()
        node = self.get_node(check_object_permissions=False)
        context['wiki_addon'] = node.get_addon('wiki')
        context['forward_addon'] = node.get_addon('forward')
        return context

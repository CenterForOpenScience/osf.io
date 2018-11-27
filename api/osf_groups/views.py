from django.apps import apps

from rest_framework import generics, permissions as drf_permissions, exceptions
from rest_framework.exceptions import NotFound
from guardian.shortcuts import get_perms

from api.base import permissions as base_permissions
from api.base.filters import ListFilterMixin
from api.base.utils import get_object_or_error, get_user_auth
from api.base.views import JSONAPIBaseView
from api.base import generic_bulk_views as bulk_views
from api.base.parsers import JSONAPIMultipleRelationshipsParser, JSONAPIMultipleRelationshipsParserForRegularJSON
from api.osf_groups.permissions import IsGroupManager
from api.osf_groups.serializers import (
    OSFGroupSerializer,
    OSFGroupDetailSerializer,
    OSFGroupMemberSerializer,
    OSFGroupMemberDetailSerializer,
    OSFGroupMemberCreateSerializer,
)
from api.users.serializers import UserSerializer
from api.users.views import UserMixin
from framework.auth.oauth_scopes import CoreScopes
from osf.models import OSFGroup
from osf.utils.permissions import MANAGER, MEMBER


class OSFGroupMixin(object):
    """
    Mixin with convenience method for retrieving the current OSF Group
    """
    group_lookup_url_kwarg = 'group_id'

    def get_osf_group(self, check_object_permissions=True):

        group = get_object_or_error(
            OSFGroup,
            self.kwargs[self.group_lookup_url_kwarg],
            self.request,
            display_name='osf_group',
        )

        if check_object_permissions:
            self.check_object_permissions(self.request, group)
        return group

    def get_node_group_perms(self, group, node):
        return get_perms(group.member_group, node)


class OSFGroupList(JSONAPIBaseView, generics.ListCreateAPIView, ListFilterMixin, OSFGroupMixin):
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )
    required_read_scopes = [CoreScopes.OSF_GROUPS_READ]
    required_write_scopes = [CoreScopes.OSF_GROUPS_WRITE]
    model_class = apps.get_model('osf.OSFGroup')

    parser_classes = (JSONAPIMultipleRelationshipsParser, JSONAPIMultipleRelationshipsParserForRegularJSON,)
    serializer_class = OSFGroupSerializer
    view_category = 'osf_groups'
    view_name = 'group-list'
    ordering = ('-modified', )

    def get_default_queryset(self):
        return OSFGroup.objects.all()

    # overrides ListCreateAPIView
    def get_queryset(self):
        return self.get_queryset_from_request()

    # overrides ListCreateAPIView
    def perform_create(self, serializer):
        """Create an OSFGroup.

        :param serializer:
        """
        # On creation, logged in user is the creator
        user = self.request.user
        serializer.save(creator=user)


class OSFGroupDetail(JSONAPIBaseView, generics.RetrieveUpdateDestroyAPIView, OSFGroupMixin):
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
        IsGroupManager,
    )
    required_read_scopes = [CoreScopes.OSF_GROUPS_READ]
    required_write_scopes = [CoreScopes.OSF_GROUPS_WRITE]
    model_class = apps.get_model('osf.OSFGroup')

    parser_classes = (JSONAPIMultipleRelationshipsParser, JSONAPIMultipleRelationshipsParserForRegularJSON,)
    serializer_class = OSFGroupDetailSerializer
    view_category = 'osf_groups'
    view_name = 'group-detail'
    ordering = ('-modified', )

    # Overrides RetrieveUpdateDestroyAPIView
    def get_object(self):
        return self.get_osf_group()

    # Overrides RetrieveUpdateDestroyAPIView
    def perform_destroy(self, instance):
        auth = get_user_auth(self.request)
        instance.remove_group(auth=auth)


class OSFGroupManagersList(JSONAPIBaseView, generics.ListAPIView, OSFGroupMixin):
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )
    required_read_scopes = [CoreScopes.OSF_GROUPS_READ]
    required_write_scopes = [CoreScopes.NULL]

    model_class = apps.get_model('osf.OSFUser')
    serializer_class = UserSerializer
    view_category = 'osf_groups'
    view_name = 'group-managers'
    ordering = ('-modified', )

    # Overrides ListAPIView
    def get_queryset(self):
        return self.get_osf_group().managers


class OSFGroupMemberBaseView(JSONAPIBaseView, OSFGroupMixin):
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
        IsGroupManager,
    )
    required_read_scopes = [CoreScopes.OSF_GROUPS_READ]
    required_write_scopes = [CoreScopes.OSF_GROUPS_WRITE]

    model_class = apps.get_model('osf.OSFUser')
    serializer_class = OSFGroupMemberSerializer
    view_category = 'osf_groups'
    ordering = ('-modified', )

    def get_serializer_class(self):
        if self.request.method == 'PUT' or self.request.method == 'PATCH' or self.request.method == 'DELETE':
            return OSFGroupMemberDetailSerializer
        elif self.request.method == 'POST':
            return OSFGroupMemberCreateSerializer
        else:
            return OSFGroupMemberSerializer


class OSFGroupMembersList(OSFGroupMemberBaseView, bulk_views.BulkUpdateJSONAPIView, bulk_views.BulkDestroyJSONAPIView, bulk_views.ListBulkCreateJSONAPIView):
    view_name = 'group-members'

    # Overrides ListAPIView
    def get_queryset(self):
        return self.get_osf_group().members

    def get_serializer_context(self):
        context = super(OSFGroupMembersList, self).get_serializer_context()
        context['group'] = self.get_osf_group()
        return context


class OSFGroupMemberDetail(OSFGroupMemberBaseView, generics.RetrieveUpdateDestroyAPIView, UserMixin):
    view_name = 'group-member-detail'

    def get_object(self):
        group = self.get_osf_group()
        user = self.get_user()
        self.check_object_permissions(self.request, user)
        # Checking group membership instead of permissions, so unregistered members are
        # recognized as group members
        if not group.is_member(user):
            raise NotFound('{} cannot be found in this OSFGroup'.format(user._id))
        return user

    def get_serializer_context(self):
        context = super(OSFGroupMemberDetail, self).get_serializer_context()
        context['group'] = self.get_osf_group()
        return context

    # overrides DestroyAPIView
    def perform_destroy(self, instance):
        group = self.get_osf_group()
        auth = get_user_auth(self.request)
        methods = {
            MANAGER: group.remove_manager,
            MEMBER: group.remove_member,
        }
        try:
            methods[instance.group_role(group)](instance, auth)
        except ValueError as e:
            raise exceptions.ValidationError(detail=e)

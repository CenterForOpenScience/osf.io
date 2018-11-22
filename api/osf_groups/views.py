from django.apps import apps

from rest_framework import generics, permissions as drf_permissions
from guardian.shortcuts import get_perms

from api.base import permissions as base_permissions
from api.base.filters import ListFilterMixin
from api.base.utils import get_object_or_error, get_user_auth
from api.base.views import JSONAPIBaseView
from api.base.parsers import JSONAPIMultipleRelationshipsParser, JSONAPIMultipleRelationshipsParserForRegularJSON
from api.osf_groups.permissions import IsGroupManager
from api.osf_groups.serializers import OSFGroupSerializer, OSFGroupDetailSerializer
from api.users.serializers import UserSerializer
from framework.auth.oauth_scopes import CoreScopes
from osf.models import OSFGroup


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


class OSFGroupMembersList(JSONAPIBaseView, generics.ListAPIView, OSFGroupMixin):
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )
    required_read_scopes = [CoreScopes.OSF_GROUPS_READ]
    required_write_scopes = [CoreScopes.NULL]

    model_class = apps.get_model('osf.OSFUser')
    serializer_class = UserSerializer
    view_category = 'osf_groups'
    view_name = 'group-members'
    ordering = ('-modified', )

    # Overrides ListAPIView
    def get_queryset(self):
        return self.get_osf_group().members_only

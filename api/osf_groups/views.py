from django.apps import apps
from django.db.models import Q

from rest_framework import generics, permissions as drf_permissions
from rest_framework.exceptions import NotFound, ValidationError

from api.base import permissions as base_permissions
from api.base.exceptions import InvalidFilterOperator, InvalidFilterValue
from api.base.filters import ListFilterMixin
from api.base.utils import get_object_or_error, get_user_auth, is_bulk_request
from api.base.views import JSONAPIBaseView
from api.base import generic_bulk_views as bulk_views
from api.base.waffle_decorators import require_flag
from api.osf_groups.permissions import IsGroupManager, GroupMemberManagement
from api.osf_groups.serializers import (
    GroupSerializer,
    GroupDetailSerializer,
    GroupMemberSerializer,
    GroupMemberDetailSerializer,
    GroupMemberCreateSerializer,
)
from api.users.views import UserMixin
from framework.auth.oauth_scopes import CoreScopes
from osf.features import OSF_GROUPS
from osf.models import OSFGroup, OSFUser
from osf.utils.permissions import MANAGER, GROUP_ROLES


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


class GroupBaseView(JSONAPIBaseView, OSFGroupMixin):
    required_read_scopes = [CoreScopes.OSF_GROUPS_READ]
    required_write_scopes = [CoreScopes.OSF_GROUPS_WRITE]
    model_class = apps.get_model('osf.OSFGroup')

    view_category = 'groups'


class GroupList(GroupBaseView, generics.ListCreateAPIView, ListFilterMixin):
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    serializer_class = GroupSerializer
    view_name = 'group-list'
    ordering = ('-modified', )

    @require_flag(OSF_GROUPS)
    def get_default_queryset(self):
        user = self.request.user
        if user.is_anonymous:
            return OSFGroup.objects.none()
        return user.osf_groups

    # overrides ListCreateAPIView
    def get_queryset(self):
        return self.get_queryset_from_request()

    # overrides ListCreateAPIView
    @require_flag(OSF_GROUPS)
    def perform_create(self, serializer):
        """Create an OSFGroup.

        :param serializer:
        """
        # On creation, logged in user is the creator
        user = self.request.user
        serializer.save(creator=user)


class GroupDetail(GroupBaseView, generics.RetrieveUpdateDestroyAPIView):
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
        IsGroupManager,
    )

    serializer_class = GroupDetailSerializer
    view_name = 'group-detail'

    # Overrides RetrieveUpdateDestroyAPIView
    @require_flag(OSF_GROUPS)
    def get_object(self):
        return self.get_osf_group()

    # Overrides RetrieveUpdateDestroyAPIView
    @require_flag(OSF_GROUPS)
    def perform_destroy(self, instance):
        auth = get_user_auth(self.request)
        instance.remove_group(auth=auth)


class OSFGroupMemberBaseView(JSONAPIBaseView, OSFGroupMixin):
    """
    Base group used for OSFGroupMemberList and OSFGroupMemberDetail
    """
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
        IsGroupManager,
    )
    required_read_scopes = [CoreScopes.OSF_GROUPS_READ]
    required_write_scopes = [CoreScopes.OSF_GROUPS_WRITE]

    model_class = apps.get_model('osf.OSFUser')
    serializer_class = GroupMemberSerializer
    view_category = 'groups'
    ordering = ('-modified', )

    def _assert_member_belongs_to_group(self, user):
        group = self.get_osf_group()
        # Checking group membership instead of permissions, so unregistered members are
        # recognized as group members
        if not group.is_member(user):
            raise NotFound('{} cannot be found in this OSFGroup'.format(user._id))

    def get_serializer_class(self):
        if self.request.method in ('PUT', 'PATCH', 'DELETE'):
            return GroupMemberDetailSerializer
        elif self.request.method == 'POST':
            return GroupMemberCreateSerializer
        else:
            return GroupMemberSerializer

    # overrides DestroyAPIView
    @require_flag(OSF_GROUPS)
    def perform_destroy(self, instance):
        group = self.get_osf_group()
        auth = get_user_auth(self.request)
        try:
            group.remove_member(instance, auth)
        except ValueError as e:
            raise ValidationError(detail=str(e))


class GroupMembersList(OSFGroupMemberBaseView, bulk_views.BulkUpdateJSONAPIView, bulk_views.BulkDestroyJSONAPIView, bulk_views.ListBulkCreateJSONAPIView, ListFilterMixin):
    view_name = 'group-members'

    # Overrides ListBulkCreateJSONAPIView
    def get_queryset(self):
        queryset = self.get_queryset_from_request()
        if is_bulk_request(self.request):
            user_ids = []
            for user in self.request.data:
                try:
                    user_id = user['id'].split('-')[1]
                except AttributeError:
                    raise ValidationError('Member identifier not provided.')
                except IndexError:
                    raise ValidationError('Member identifier incorrectly formatted.')
                else:
                    user_ids.append(user_id)
            queryset = queryset.filter(guids___id__in=user_ids)
        return queryset

    # Overrides ListFilterMixin
    @require_flag(OSF_GROUPS)
    def get_default_queryset(self):
        # Returns all members and managers of the OSF Group (User objects)
        return self.get_osf_group().members

    # Overrides ListBulkCreateJSONAPIView
    def get_serializer_context(self):
        context = super(GroupMembersList, self).get_serializer_context()
        # Permissions check handled here - needed when performing write operations
        context['group'] = self.get_osf_group()
        return context

    # Overrides BulkDestroyJSONAPIView
    def get_requested_resources(self, request, request_data):
        requested_ids = []
        for data in request_data:
            try:
                requested_ids.append(data['id'].split('-')[1])
            except IndexError:
                raise ValidationError('Member identifier incorrectly formatted.')

        resource_object_list = OSFUser.objects.filter(guids___id__in=requested_ids)
        for resource in resource_object_list:
            self._assert_member_belongs_to_group(resource)

        if len(resource_object_list) != len(request_data):
            raise ValidationError({'non_field_errors': 'Could not find all objects to delete.'})

        return resource_object_list

    # Overrides ListFilterMixin
    def build_query_from_field(self, field_name, operation):
        if field_name == 'role':
            if operation['op'] != 'eq':
                raise InvalidFilterOperator(value=operation['op'], valid_operators=['eq'])
            # operation['value'] should be 'member' or 'manager'
            role = operation['value'].lower().strip()
            if role not in GROUP_ROLES:
                raise InvalidFilterValue(value=operation['value'])
            group = self.get_osf_group(check_object_permissions=False)
            return Q(id__in=group.managers if role == MANAGER else group.members_only)
        return super(GroupMembersList, self).build_query_from_field(field_name, operation)

    @require_flag(OSF_GROUPS)
    def perform_create(self, serializer):
        return super(GroupMembersList, self).perform_create(serializer)


class GroupMemberDetail(OSFGroupMemberBaseView, generics.RetrieveUpdateDestroyAPIView, UserMixin):
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
        GroupMemberManagement,
    )
    view_name = 'group-member-detail'

    # Overrides RetrieveUpdateDestroyAPIView
    @require_flag(OSF_GROUPS)
    def get_object(self):
        user = self.get_user()
        self._assert_member_belongs_to_group(user)
        return user

    # Overrides RetrieveUpdateDestroyAPIView
    def get_serializer_context(self):
        context = super(GroupMemberDetail, self).get_serializer_context()
        context['group'] = self.get_osf_group(check_object_permissions=False)
        return context

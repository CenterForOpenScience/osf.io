import requests
from rest_framework import generics, permissions as drf_permissions
from modularodm import Q
from rest_framework.exceptions import PermissionDenied, ValidationError

from framework.auth.core import Auth
from api.base.utils import get_object_or_404, waterbutler_url_for
from website.models import Node
from api.base.filters import ODMFilterMixin
from api.registrations.serializers import RegistrationSerializer
from api.nodes.serializers import NodePointersSerializer
from api.nodes.views import NodeMixin, NodeFilesList, NodeChildrenList, NodeContributorsList, NodeDetail

from api.nodes.permissions import ContributorOrPublic, ReadOnlyIfRegistration


class RegistrationMixin(NodeMixin):
    """Mixin with convenience methods for retrieving the current node based on the
    current URL. By default, fetches the current node based on the pk kwarg.
    """

    serializer_class = RegistrationSerializer
    node_lookup_url_kwarg = 'registration_id'


class RegistrationList(generics.ListAPIView, ODMFilterMixin):
    """All node registrations"""

    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
    )
    serializer_class = RegistrationSerializer

    # overrides ODMFilterMixin
    def get_default_odm_query(self):
        base_query = (
            Q('is_deleted', 'ne', True) &
            Q('is_folder', 'ne', True) &
            (Q('is_registration', 'eq', True) | Q('is_registration_draft', 'eq', True))
        )
        user = self.request.user
        permission_query = Q('is_public', 'eq', True)
        if not user.is_anonymous():
            permission_query = (Q('is_public', 'eq', True) | Q('contributors', 'icontains', user._id))

        query = base_query & permission_query
        return query

    # overrides ListCreateAPIView
    def get_queryset(self):
        query = self.get_query_from_request()
        return Node.find(query)

# TODO: Return project details for nodes that are registration_drafts in addition to registrations

class RegistrationDetail(NodeDetail, RegistrationMixin):
    """
    Registration details
    """
    permission_classes = (
        ContributorOrPublic,
        ReadOnlyIfRegistration,
    )
    serializer_class = RegistrationSerializer

    # overrides RetrieveAPIView
    def get_object(self):
        node = self.get_node()
        if node.is_registration == False and node.is_registration_draft == False:
            raise ValidationError('Not a registration or registration draft.')
        return self.get_node()

    # overrides RetrieveUpdateAPIView
    def get_serializer_context(self):
        # Serializer needs the request in order to make an update to privacy
        return {'request': self.request}


class RegistrationContributorsList(NodeContributorsList, RegistrationMixin):
    """
    Contributors(users) for a registration
    """
    def get_default_queryset(self):
        node = self.get_node()
        if node.is_registration == False:
            raise ValidationError('Node is not registration.')
        visible_contributors = node.visible_contributor_ids
        contributors = []
        for contributor in node.contributors:
            contributor.bibliographic = contributor._id in visible_contributors
            contributors.append(contributor)
        return contributors


class RegistrationChildrenList(NodeChildrenList, RegistrationMixin):
    """
    Children of the current registration
    """
    def get_queryset(self):
        node = self.get_node()
        if node.is_registration == False:
            raise ValidationError('Not a registration.')
        nodes = node.nodes
        user = self.request.user
        if user.is_anonymous():
            auth = Auth(None)
        else:
            auth = Auth(user)
        children = [node for node in nodes if node.can_view(auth) and node.primary]
        return children


class RegistrationPointersList(generics.ListAPIView, RegistrationMixin):
    """
    Registration pointers
    """

    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        ContributorOrPublic,
    )

    serializer_class = NodePointersSerializer

    def get_queryset(self):
        node = self.get_node()
        if node.is_registration == False:
            raise ValidationError('Not a registration.')
        return self.get_node()
        pointers = node.nodes_pointer
        return pointers


class RegistrationFilesList(NodeFilesList, RegistrationMixin):
    """
    Files attached to a registration
    """
    def get_queryset(self):
        query_params = self.request.query_params
        node = self.get_node()
        if node.is_registration == False:
            raise ValidationError('Node is not registration.')
        addons = self.get_nodes().get_addons()
        user = self.request.user
        cookie = None if self.request.user.is_anonymous() else user.get_or_create_cookie()
        node_id = self.get_nodes()._id
        obj_args = self.request.parser_context['args']

        provider = query_params.get('provider')
        path = query_params.get('path', '/')
        files = []

        if provider is None:
            valid_self_link_methods = self.get_valid_self_link_methods(True)
            for addon in addons:
                if addon.config.has_hgrid_files:
                    files.append({
                        'valid_self_link_methods': valid_self_link_methods['folder'],
                        'provider': addon.config.short_name,
                        'name': addon.config.short_name,
                        'path': path,
                        'node_id': node_id,
                        'cookie': cookie,
                        'args': obj_args,
                        'waterbutler_type': 'file',
                        'item_type': 'folder',
                        'metadata': {},
                    })
        else:
            url = waterbutler_url_for('data', provider, path, self.kwargs['node_id'], cookie, obj_args)
            waterbutler_request = requests.get(url)
            if waterbutler_request.status_code == 401:
                raise PermissionDenied
            try:
                waterbutler_data = waterbutler_request.json()['data']
            except KeyError:
                raise ValidationError(detail='detail: Could not retrieve files information.')

            if isinstance(waterbutler_data, list):
                for item in waterbutler_data:
                    file = self.get_file_item(item, cookie, obj_args)
                    files.append(file)
            else:
                files.append(self.get_file_item(waterbutler_data, cookie, obj_args))

        return files

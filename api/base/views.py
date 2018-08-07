from collections import defaultdict

from django_bulk_update.helper import bulk_update
from django.conf import settings as django_settings
from django.db import transaction
from django.db.models import F
from django.http import JsonResponse
from django.contrib.contenttypes.models import ContentType
from rest_framework import generics
from rest_framework import permissions as drf_permissions
from rest_framework import status
from rest_framework.decorators import api_view, throttle_classes
from rest_framework.exceptions import ValidationError, NotFound
from rest_framework.mixins import ListModelMixin
from rest_framework.response import Response

from api.base import permissions as base_permissions
from api.base import utils
from api.base.exceptions import RelationshipPostMakesNoChanges
from api.base.filters import ListFilterMixin
from api.base.parsers import JSONAPIRelationshipParser
from api.base.parsers import JSONAPIRelationshipParserForRegularJSON
from api.base.requests import EmbeddedRequest
from api.base.serializers import (
    MaintenanceStateSerializer,
    LinkedNodesRelationshipSerializer,
    LinkedRegistrationsRelationshipSerializer
)
from api.base.throttling import RootAnonThrottle, UserRateThrottle
from api.base.utils import is_bulk_request, get_user_auth
from api.nodes.utils import get_file_object
from api.nodes.permissions import ContributorOrPublic
from api.nodes.permissions import ContributorOrPublicForRelationshipPointers
from api.nodes.permissions import ReadOnlyIfRegistration
from api.users.serializers import UserSerializer
from framework.auth.oauth_scopes import CoreScopes
from osf.models import Contributor, MaintenanceState, BaseFileNode
from waffle.models import Flag
from waffle import flag_is_active

class JSONAPIBaseView(generics.GenericAPIView):

    def __init__(self, **kwargs):
        assert getattr(self, 'view_name', None), 'Must specify view_name on view.'
        assert getattr(self, 'view_category', None), 'Must specify view_category on view.'
        self.view_fqn = ':'.join([self.view_category, self.view_name])
        super(JSONAPIBaseView, self).__init__(**kwargs)

    def _get_embed_partial(self, field_name, field):
        """Create a partial function to fetch the values of an embedded field. A basic
        example is to include a Node's children in a single response.

        :param str field_name: Name of field of the view's serializer_class to load
        results for
        :return function object -> dict:
        """
        if getattr(field, 'field', None):
            field = field.field

        def partial(item):
            # resolve must be implemented on the field
            v, view_args, view_kwargs = field.resolve(item, field_name, self.request)
            if not v:
                return None

            if isinstance(self.request, EmbeddedRequest):
                request = EmbeddedRequest(self.request._request)
            else:
                request = EmbeddedRequest(self.request)

            if not hasattr(request._request._request, '_embed_cache'):
                request._request._request._embed_cache = {}
            cache = request._request._request._embed_cache

            request.parents.setdefault(type(item), {})[item._id] = item

            view_kwargs.update({
                'request': request,
                'is_embedded': True,
            })

            # Setup a view ourselves to avoid all the junk DRF throws in
            # v is a function that hides everything v.cls is the actual view class
            view = v.cls()
            view.args = view_args
            view.kwargs = view_kwargs
            view.request = request
            view.request.parser_context['kwargs'] = view_kwargs
            view.format_kwarg = view.get_format_suffix(**view_kwargs)

            if not isinstance(view, ListModelMixin):
                try:
                    item = view.get_object()
                except Exception as e:
                    with transaction.atomic():
                        ret = view.handle_exception(e).data
                    return ret

            _cache_key = (v.cls, field_name, view.get_serializer_class(), (type(item), item.id))
            if _cache_key in cache:
                # We already have the result for this embed, return it
                return cache[_cache_key]

            # Cache serializers. to_representation of a serializer should NOT augment it's fields so resetting the context
            # should be sufficient for reuse
            if not view.get_serializer_class() in cache:
                cache[view.get_serializer_class()] = view.get_serializer_class()(many=isinstance(view, ListModelMixin), context=view.get_serializer_context())
            ser = cache[view.get_serializer_class()]

            try:
                ser._context = view.get_serializer_context()

                if not isinstance(view, ListModelMixin):
                    ret = ser.to_representation(item)
                else:
                    queryset = view.filter_queryset(view.get_queryset())
                    page = view.paginate_queryset(getattr(queryset, '_results_cache', None) or queryset)

                    ret = ser.to_representation(page or queryset)

                    if page is not None:
                        request.parser_context['view'] = view
                        request.parser_context['kwargs'].pop('request')
                        view.paginator.request = request
                        ret = view.paginator.get_paginated_response(ret).data
            except Exception as e:
                with transaction.atomic():
                    ret = view.handle_exception(e).data

            # Allow request to be gc'd
            ser._context = None

            # Cache our final result
            cache[_cache_key] = ret

            return ret

        return partial

    def get_serializer_context(self):
        """Inject request into the serializer context. Additionally, inject partial functions
        (request, object -> embed items) if the query string contains embeds.  Allows
         multiple levels of nesting.
        """
        context = super(JSONAPIBaseView, self).get_serializer_context()
        if self.kwargs.get('is_embedded'):
            embeds = []
        else:
            embeds = self.request.query_params.getlist('embed') or self.request.query_params.getlist('embed[]')

        fields_check = self.get_serializer_class()._declared_fields.copy()
        if 'fields[{}]'.format(self.serializer_class.Meta.type_) in self.request.query_params:
            # Check only requested and mandatory fields
            sparse_fields = self.request.query_params['fields[{}]'.format(self.serializer_class.Meta.type_)]
            for field in fields_check.copy().keys():
                if field not in ('type', 'id', 'links') and field not in sparse_fields:
                    fields_check.pop(field)

        for field in fields_check:
            if getattr(fields_check[field], 'field', None):
                fields_check[field] = fields_check[field].field

        for field in fields_check:
            if getattr(fields_check[field], 'always_embed', False) and field not in embeds:
                embeds.append(unicode(field))
            if getattr(fields_check[field], 'never_embed', False) and field in embeds:
                embeds.remove(field)
        embeds_partials = {}
        for embed in embeds:
            embed_field = fields_check.get(embed)
            embeds_partials[embed] = self._get_embed_partial(embed, embed_field)

        context.update({
            'enable_esi': (
                utils.is_truthy(self.request.query_params.get('esi', django_settings.ENABLE_ESI)) and
                self.request.accepted_renderer.media_type in django_settings.ESI_MEDIA_TYPES
            ),
            'embed': embeds_partials,
            'envelope': self.request.query_params.get('envelope', 'data'),
        })
        return context


class LinkedNodesRelationship(JSONAPIBaseView, generics.RetrieveUpdateDestroyAPIView, generics.CreateAPIView):
    """ Relationship Endpoint for Linked Node relationships

    Used to set, remove, update and retrieve the ids of the linked nodes attached to this collection. For each id, there
    exists a node link that contains that node.

    ##Actions

    ###Create

        Method:        POST
        URL:           /links/self
        Query Params:  <none>
        Body (JSON):   {
                         "data": [{
                           "type": "linked_nodes",   # required
                           "id": <node_id>   # required
                         }]
                       }
        Success:       201

    This requires both edit permission on the collection, and for the user that is
    making the request to be able to read the nodes requested. Data can contain any number of
    node identifiers. This will create a node_link for all node_ids in the request that
    do not currently have a corresponding node_link in this collection.

    ###Update

        Method:        PUT || PATCH
        URL:           /links/self
        Query Params:  <none>
        Body (JSON):   {
                         "data": [{
                           "type": "linked_nodes",   # required
                           "id": <node_id>   # required
                         }]
                       }
        Success:       200

    This requires both edit permission on the collection and for the user that is
    making the request to be able to read the nodes requested. Data can contain any number of
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
                           "type": "linked_nodes",   # required
                           "id": <node_id>   # required
                         }]
                       }
        Success:       204

    This requires edit permission on the node. This will delete any node_links that have a
    corresponding node_id in the request.
    """
    permission_classes = (
        ContributorOrPublicForRelationshipPointers,
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
        ReadOnlyIfRegistration,
    )

    required_read_scopes = [CoreScopes.NODE_LINKS_READ]
    required_write_scopes = [CoreScopes.NODE_LINKS_WRITE]

    serializer_class = LinkedNodesRelationshipSerializer
    parser_classes = (JSONAPIRelationshipParser, JSONAPIRelationshipParserForRegularJSON, )

    def get_object(self):
        object = self.get_node(check_object_permissions=False)
        auth = utils.get_user_auth(self.request)
        obj = {'data': [
            pointer for pointer in
            object.linked_nodes.filter(is_deleted=False, type='osf.node')
            if pointer.can_view(auth)
        ], 'self': object}
        self.check_object_permissions(self.request, obj)
        return obj

    def perform_destroy(self, instance):
        data = self.request.data['data']
        auth = utils.get_user_auth(self.request)
        current_pointers = {pointer._id: pointer for pointer in instance['data']}
        collection = instance['self']
        for val in data:
            if val['id'] in current_pointers:
                collection.rm_pointer(current_pointers[val['id']], auth)

    def create(self, *args, **kwargs):
        try:
            ret = super(LinkedNodesRelationship, self).create(*args, **kwargs)
        except RelationshipPostMakesNoChanges:
            return Response(status=status.HTTP_204_NO_CONTENT)
        return ret


class LinkedRegistrationsRelationship(JSONAPIBaseView, generics.RetrieveUpdateDestroyAPIView, generics.CreateAPIView):
    """ Relationship Endpoint for Linked Registrations relationships

    Used to set, remove, update and retrieve the ids of the linked registrations attached to this collection. For each id, there
    exists a node link that contains that registration.

    ##Actions

    ###Create

        Method:        POST
        URL:           /links/self
        Query Params:  <none>
        Body (JSON):   {
                         "data": [{
                           "type": "linked_registrations",   # required
                           "id": <node_id>   # required
                         }]
                       }
        Success:       201

    This requires both edit permission on the collection, and for the user that is
    making the request to be able to read the registrations requested. Data can contain any number of
    node identifiers. This will create a node_link for all node_ids in the request that
    do not currently have a corresponding node_link in this collection.

    ###Update

        Method:        PUT || PATCH
        URL:           /links/self
        Query Params:  <none>
        Body (JSON):   {
                         "data": [{
                           "type": "linked_registrations",   # required
                           "id": <node_id>   # required
                         }]
                       }
        Success:       200

    This requires both edit permission on the collection and for the user that is
    making the request to be able to read the registrations requested. Data can contain any number of
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
                           "type": "linked_registrations",   # required
                           "id": <node_id>   # required
                         }]
                       }
        Success:       204

    This requires edit permission on the node. This will delete any node_links that have a
    corresponding node_id in the request.
    """
    permission_classes = (
        ContributorOrPublicForRelationshipPointers,
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
        ReadOnlyIfRegistration,
    )

    required_read_scopes = [CoreScopes.NODE_LINKS_READ]
    required_write_scopes = [CoreScopes.NODE_LINKS_WRITE]

    serializer_class = LinkedRegistrationsRelationshipSerializer
    parser_classes = (JSONAPIRelationshipParser, JSONAPIRelationshipParserForRegularJSON, )

    def get_object(self):
        object = self.get_node(check_object_permissions=False)
        auth = utils.get_user_auth(self.request)
        obj = {'data': [
            pointer for pointer in
            object.linked_nodes.filter(is_deleted=False, type='osf.registration')
            if pointer.can_view(auth)
        ], 'self': object}
        self.check_object_permissions(self.request, obj)
        return obj

    def perform_destroy(self, instance):
        data = self.request.data['data']
        auth = utils.get_user_auth(self.request)
        current_pointers = {pointer._id: pointer for pointer in instance['data']}
        collection = instance['self']
        for val in data:
            if val['id'] in current_pointers:
                collection.rm_pointer(current_pointers[val['id']], auth)
            else:
                raise NotFound(detail='Pointer with id "{}" not found in pointers list'.format(val['id'], collection))

    def create(self, *args, **kwargs):
        try:
            ret = super(LinkedRegistrationsRelationship, self).create(*args, **kwargs)
        except RelationshipPostMakesNoChanges:
            return Response(status=status.HTTP_204_NO_CONTENT)
        return ret


@api_view(('GET',))
@throttle_classes([RootAnonThrottle, UserRateThrottle])
def root(request, format=None, **kwargs):
    """
    The documentation for the Open Science Framework API can be found at [developer.osf.io](https://developer.osf.io).
    The contents of this endpoint are variable and subject to change without notification.
    """
    if request.user and not request.user.is_anonymous:
        user = request.user
        current_user = UserSerializer(user, context={'request': request}).data
    else:
        current_user = None
    flags = [name for name in Flag.objects.values_list('name', flat=True) if flag_is_active(request, name)]
    kwargs = request.parser_context['kwargs']
    return_val = {
        'meta': {
            'message': 'Welcome to the OSF API.',
            'version': request.version,
            'current_user': current_user,
            'active_flags': flags,
        },
        'links': {
            'nodes': utils.absolute_reverse('nodes:node-list', kwargs=kwargs),
            'users': utils.absolute_reverse('users:user-list', kwargs=kwargs),
            'collections': utils.absolute_reverse('collections:collection-list', kwargs=kwargs),
            'registrations': utils.absolute_reverse('registrations:registration-list', kwargs=kwargs),
            'institutions': utils.absolute_reverse('institutions:institution-list', kwargs=kwargs),
            'licenses': utils.absolute_reverse('licenses:license-list', kwargs=kwargs),
            'schemas': utils.absolute_reverse('schemas:registration-schema-list', kwargs=kwargs),
            'addons': utils.absolute_reverse('addons:addon-list', kwargs=kwargs),
        }
    }

    if utils.has_admin_scope(request):
        return_val['meta']['admin'] = True

    return Response(return_val)

@api_view(('GET',))
@throttle_classes([RootAnonThrottle, UserRateThrottle])
def status_check(request, format=None, **kwargs):
    maintenance = MaintenanceState.objects.all().first()
    return Response({
        'maintenance': MaintenanceStateSerializer(maintenance).data if maintenance else None
    })


def error_404(request, format=None, *args, **kwargs):
    return JsonResponse(
        {'errors': [{'detail': 'Not found.'}]},
        status=404,
        content_type='application/vnd.api+json; application/json'
    )


class BaseContributorDetail(JSONAPIBaseView, generics.RetrieveAPIView):

    # overrides RetrieveAPIView
    def get_object(self):
        node = self.get_node()
        user = self.get_user()
        # May raise a permission denied
        self.check_object_permissions(self.request, user)
        try:
            return node.contributor_set.get(user=user)
        except Contributor.DoesNotExist:
            raise NotFound('{} cannot be found in the list of contributors.'.format(user))


class BaseContributorList(JSONAPIBaseView, generics.ListAPIView, ListFilterMixin):

    ordering = ('-modified',)

    def get_default_queryset(self):
        node = self.get_node()

        return node.contributor_set.all().include('user__guids')

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
            queryset[:] = [contrib for contrib in queryset if contrib._id in contrib_ids]
        return queryset


class BaseNodeLinksDetail(JSONAPIBaseView, generics.RetrieveAPIView):
    pass


class BaseNodeLinksList(JSONAPIBaseView, generics.ListAPIView):

    ordering = ('-modified',)

    def get_queryset(self):
        auth = get_user_auth(self.request)
        query = self.get_node()\
                .node_relations.select_related('child')\
                .filter(is_node_link=True, child__is_deleted=False)\
                .exclude(child__type='osf.collection')
        return sorted([
            node_link for node_link in query
            if node_link.child.can_view(auth) and not node_link.child.is_retracted
        ], key=lambda node_link: node_link.child.modified, reverse=True)


class BaseLinkedList(JSONAPIBaseView, generics.ListAPIView):

    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        ContributorOrPublic,
        ReadOnlyIfRegistration,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.NODE_LINKS_READ]
    required_write_scopes = [CoreScopes.NULL]

    # subclass must set
    serializer_class = None
    view_category = None
    view_name = None

    ordering = ('-modified',)

    # TODO: This class no longer exists
    # model_class = Pointer

    def get_queryset(self):
        auth = get_user_auth(self.request)

        return (
            self.get_node().linked_nodes
            .filter(is_deleted=False)
            .annotate(region=F('addons_osfstorage_node_settings__region___id'))
            .exclude(region=None)
            .exclude(type='osf.collection', region=None)
            .can_view(user=auth.user, private_link=auth.private_link)
            .order_by('-modified')
        )


class WaterButlerMixin(object):

    path_lookup_url_kwarg = 'path'
    provider_lookup_url_kwarg = 'provider'

    def bulk_get_file_nodes_from_wb_resp(self, files_list):
        """Takes a list of file data from wb response, touches/updates metadata for each, and returns list of file objects.
        This function mirrors all the actions of get_file_node_from_wb_resp except the create and updates are done in bulk.
        The bulk_update and bulk_create do not call the base class update and create so the actions of those functions are
        done here where needed
        """
        node = self.get_node(check_object_permissions=False)
        content_type = ContentType.objects.get_for_model(node)

        objs_to_create = defaultdict(lambda: [])
        file_objs = []

        for item in files_list:
            attrs = item['attributes']
            base_class = BaseFileNode.resolve_class(
                attrs['provider'],
                BaseFileNode.FOLDER if attrs['kind'] == 'folder'
                else BaseFileNode.FILE
            )

            # mirrors BaseFileNode get_or_create
            try:
                file_obj = base_class.objects.get(target_object_id=node.id, target_content_type=content_type, _path='/' + attrs['path'].lstrip('/'))
            except base_class.DoesNotExist:
                # create method on BaseFileNode appends provider, bulk_create bypasses this step so it is added here
                file_obj = base_class(target=node, _path='/' + attrs['path'].lstrip('/'), provider=base_class._provider)
                objs_to_create[base_class].append(file_obj)
            else:
                file_objs.append(file_obj)

            file_obj.update(None, attrs, user=self.request.user, save=False)

        bulk_update(file_objs)

        for base_class in objs_to_create:
            base_class.objects.bulk_create(objs_to_create[base_class])
            file_objs += objs_to_create[base_class]

        return file_objs

    def get_file_node_from_wb_resp(self, item):
        """Takes file data from wb response, touches/updates metadata for it, and returns file object"""
        attrs = item['attributes']
        file_node = BaseFileNode.resolve_class(
            attrs['provider'],
            BaseFileNode.FOLDER if attrs['kind'] == 'folder'
            else BaseFileNode.FILE
        ).get_or_create(self.get_node(check_object_permissions=False), attrs['path'])

        file_node.update(None, attrs, user=self.request.user)
        return file_node

    def fetch_from_waterbutler(self):
        node = self.get_node(check_object_permissions=False)
        path = self.kwargs[self.path_lookup_url_kwarg]
        provider = self.kwargs[self.provider_lookup_url_kwarg]
        return self.get_file_object(node, path, provider)

    def get_file_object(self, target, path, provider, check_object_permissions=True):
        obj = get_file_object(target=target, path=path, provider=provider, request=self.request)
        if provider == 'osfstorage':
            if check_object_permissions:
                self.check_object_permissions(self.request, obj)
        return obj


class DeprecatedView(JSONAPIBaseView):
    """ Mixin for deprecating old views
    Subclasses must define `max_version`
    """

    @property
    def max_version(self):
        raise NotImplementedError()

    def __init__(self, *args, **kwargs):
        super(DeprecatedView, self).__init__(*args, **kwargs)
        self.is_deprecated = False

    def determine_version(self, request, *args, **kwargs):
        version, scheme = super(DeprecatedView, self).determine_version(request, *args, **kwargs)
        if version > self.max_version:
            self.is_deprecated = True
            raise NotFound(detail='This route has been deprecated. It was last available in version {}'.format(self.max_version))
        return version, scheme

    def finalize_response(self, request, response, *args, **kwargs):
        response = super(DeprecatedView, self).finalize_response(request, response, *args, **kwargs)
        if self.is_deprecated:
            # Already has the error message
            return response
        if response.status_code == 204:
            response.status_code = 200
            response.data = {}
        deprecation_warning = 'This route is deprecated and will be unavailable after version {}'.format(self.max_version)
        if response.data.get('meta', False):
            if response.data['meta'].get('warnings', False):
                response.data['meta']['warnings'].append(deprecation_warning)
            else:
                response.data['meta']['warnings'] = [deprecation_warning]
        else:
            response.data['meta'] = {'warnings': [deprecation_warning]}
        return response

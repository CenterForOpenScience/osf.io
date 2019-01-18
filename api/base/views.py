from collections import defaultdict

from django_bulk_update.helper import bulk_update
from django.conf import settings as django_settings
from django.db import transaction
from django.http import JsonResponse
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
    """Welcome to the V2 GakuNin RDM API. With this API you can access users, projects, components, logs, and files
    from the [GakuNin RDM](https://rdm.nii.ac.jp/). The GakuNin RDM (GRDM) is a free, open-source service
    maintained by the [National Institute of Informatics](http://nii.ac.jp/).

    The OSF serves as a repository and archive for study designs, materials, data, manuscripts, or anything else
    associated with your research during the research process. Every project and file on the GakuNin RDM has a permanent unique
    identifier, and every registration (a permanent, time-stamped version of your projects and files) can be assigned a
    DOI/ARK. You can use the GakuNin RDM to measure your impact by monitoring the traffic to projects and files you make
    public. With the GakuNin RDM you have full control of what parts of your research are public and what remains private.

    Beta notice: This API is currently a beta service.  You are encouraged to use the API and will receive support
    when doing so, however, while the API remains in beta status, it may change without notice as a result of
    product updates. The temporary beta status of the API will remain in place while it matures. In a future
    release, the beta status will be removed, at which point we will provide details on how long we will support
    the API V2 and under what circumstances it might change.

    #General API Usage

    The OSF API generally conforms to the [JSON-API v1.0 spec](http://jsonapi.org/format/1.0/).  Where exceptions
    exist, they will be noted.  Each endpoint will have its own documentation, but there are some general principles.

    Assume undocumented routes/features/fields are unstable.

    ##Requests

    ###Canonical URLs

    All canonical URLs have trailing slashes.  A request to an endpoint without a trailing slash will result in a 301
    redirect to the canonical URL.  There are some exceptions when working with the Files API, so if a URL in a response
    does not have a slash, do not append one.

    ###Plurals

    Endpoints are always pluralized.  `/users/`, not `/user/`, `/nodes/`, not `/node/`.

    ###Common Actions

    Every endpoint in the GakuNin RDM API responds to `GET`, `HEAD`, and `OPTION` requests.  You must have adequate permissions
    to interact with the endpoint.  Unauthorized use will result in 401 Unauthorized or 403 Forbidden responses.  Use
    `HEAD` to probe an endpoint and make sure your headers are well-formed.  `GET` will return a representation of the
    entity or entity collection referenced by the endpoint.  An `OPTIONS` request will return a JSON object that describes the
    endpoint, including the name, a description, the acceptable request formats, the allowed response formats, and any
    actions available via the endpoint.

    ###Versioning
    Versioning can be specified in three different ways:

    1. URL Path Versioning, e.g. `/v2/` or `/v3/`

        + A version specified via the URL path is a **required** part of the URL.

        + Only a major version can be specified via the URL path, i.e. `/v2.0.6/` is invalid,
        additionally, paths such as `/v2.0/` are invalid.

        + If the default version of the API is within the major version specified in the URL path,
        the default version will be applied (i.e. if the default version is `2.3` and the URL path is `/v2/`,
        then version returned will be `2.3`).

        + If the default version of the API is not within the major version specified in the URL path,
        the URL path version will be applied (i.e. if the default version is `3.0` and the URL path is `/v2/`,
        then the version returned will be `2.0`)

    2. Query Parameter Versioning, e.g. `/v2/nodes/?version=2.1.6`

        + Pinning to a specific version via a query parameter is **optional**.

        + A specific version (major, minor, or patch) for a single request can be specified via the `version`
        query parameter, as long as it is an allowed version.

        + If the version specified in the query parameter does not fall within the same major version
         specified in the URL path, i.e `/v2/nodes/?version=3.1.4` a `409 Conflict` response will be returned.

    3.  Header Versioning, e.g. `Accept-Header=application/vnd.api+json;version=3.0.1`

        + Pinning to a specific version via request header is **optional**.

        + A specific version (major, minor, or patch) for a single request can be specified
         via the `Accept Header` of the request, as long as it is an allowed version.

        + If the version specified in the header does not fall within the same major version specified
         in the URL path a `409 Conflict` response will be returned.

        + If both a header version and query parameter version are specified, the versions must match exactly
          or a `409 Conflict` response will be returned (i.e. one does not take precedence over the other).

    ###Filtering

    Entity collections can be filtered by adding a query parameter in the form:

        filter[<fieldname>]=<matching information>

    String queries are filtered using substring matching. For example, if you were trying to find [Lise
    Meitner](http://en.wikipedia.org/wiki/Lise_Meitner):

        /users/?filter[full_name]=meitn

    You can filter on multiple fields, or the same field in different ways, by &-ing the query parameters together.

        /users/?filter[full_name]=lise&filter[family_name]=mei

    Boolean fields should be queried with `true` or `false`.

        /nodes/?filter[registered]=true

    You can request multiple resources by filtering on id and placing comma-separated values in your query parameter.

        /nodes/?filter[id]=aegu6,me23a

    You can filter with case-sensitivity or case-insensitivity by using `contains` and `icontains`, respectively.

        /nodes/?filter[tags][icontains]=help

    ###Embedding

    All related resources that appear in the `relationships` attribute are embeddable, meaning that
    by adding a query parameter like:

        /nodes/?embed=contributors

    it is possible to fetch a Node and its contributors in a single request. The embedded results will have the following
    structure:

        {relationship_name}: {full_embedded_response}

    Where `full_embedded_response` means the full API response resulting from a GET request to the `href` link of the
    corresponding related resource. This means if there are no errors in processing the embedded request the response will have
    the format:

        data: {response}

    And if there are errors processing the embedded request the response will have the format:

        errors: {errors}

    Multiple embeds can be achieved with multiple query parameters separated by "&".

        /nodes/?embed=contributors&embed=comments

    Some endpoints are automatically embedded.

    ###Pagination

    All entity collection endpoints respond to the `page` query parameter behavior as described in the [JSON-API
    pagination spec](http://jsonapi.org/format/1.0/#crud).  However, pagination links are provided in the response, and
    you are encouraged to use that rather than adding query parameters by hand.

    ###Formatting POST/PUT/PATCH request bodies

    The OSF API follows the JSON-API spec for [create and update requests](http://jsonapi.org/format/1.0/#crud).  This means
    all request bodies must be wrapped with some metadata.  Each request body must be an object with a `data` key
    containing at least a `type` member.  The value of the `type` member must agree with the `type` of the entities
    represented by the endpoint.  If not, a 409 Conflict will be returned.  The request should also contain an
    `attributes` member with an object containing the key-value pairs to be created/updated.  PUT/PATCH requests must
    also have an `id` key that matches the id part of the endpoint.  If the `id` key does not match the id path part, a
    409 Conflict error will be returned.

    ####Example 1: Creating a Node via POST

        POST /v2/nodes/
        {
          "data": {
            "type": "nodes",
            "attributes": {
              "title" : "A Phylogenetic Tree of Famous Internet Cats",
              "category" : "project",
              "description" : "How closely related are Grumpy Cat and C.H. Cheezburger? Is memefulness inheritable?"
            }
          }
        }

    ####Example 2: Updating a User via PUT

        PUT /v2/users/me/
        {
          "data": {
            "id": "3rqxc",
            "type": "users",
            "attributes": {
              "full_name" : "Henrietta Swan Leavitt",
              "given_name" : "Henrietta",
              "middle_names" : "Swan",
              "family_name" : "Leavitt"
            }
          }
        }

    **NB:** If you PUT/PATCH to the `/users/me/` endpoint, you must still provide your full user id in the `id` field of
    the request.  We do not support using the `me` alias in request bodies at this time.

    ###PUT vs. PATCH

    For most endpoints that support updates via PUT requests, we also allow PATCH updates. The only difference is that
    PUT requests require all mandatory attributes to be set, even if their value is unchanged. PATCH requests may omit
    mandatory attributes, whose value will be unchanged.

    ###Attribute Validation

    Endpoints that allow creation or modification of entities generally limit updates to certain attributes of the
    entity.  If you attempt to set an attribute that does not permit updates (such as a `created` timestamp), the
    API will silently ignore that attribute.  This will not affect the response from the API: if the request would have
    succeeded without the updated attribute, it will still report as successful.  Likewise, if the request would have
    failed without the attribute update, the API will still report a failure.

    Typoed or non-existent attributes will behave the same as non-updatable attributes and be silently ignored. If a
    request is not working the way you expect, make sure to double check your spelling.

    ##Responses

    ###Entities

    An entity is a single resource that has been retrieved from the API, usually from an endpoint with the entity's id
    as the final path part.  A successful response from an entity request will be a JSON object with a top level `data`
    key pointing to a sub-object with the following members:

    + `id`

    The identifier for the entity.  This MUST be included with [PUT and PATCH
    requests](#formatting-postputpatch-request-bodies).

    + `type`

    The type identifier of this entity.  This MUST be included with [all create/update
    requests](#formatting-postputpatch-request-bodies).

    + `attributes`

    The properties of the entity.  Names, descriptions, etc.

    + `relationships`

    Relationships are urls to other entities or entity collections that have a relationship to the entity. For example,
    the node entity provides a `contributors` relationship that points to the endpoint to retrieve all contributors to
    that node.  It is recommended to use these links rather than to id-filter general entity collection endpoints.
    They'll be faster, easier, and less error-prone.  Generally a relationship will have the following structure:

        {relationship_name}: {
            "links": {
                "related": {
                    "href": {url_to_related_entity_or_entity_collection},
                    "meta": {}
                }
            }
        }

    If there are no related entities, `href` will be null.

    + `embeds`

    Please see `Embedding` documentation under `Requests`.

    + `links`

    Links are urls to alternative representations of the entity or actions that may be performed on the entity.  Most
    entities will provide a `self` link that is the canonical endpoint for the entity where update and delete requests
    should be sent.  In-depth documentation of actions is available by navigating to the `self` link in the Browsable
    API.  Most entities will also provide an `html` link that directs to the entity's page on the [OSF](http://osf.io/).

    ###Entity Collections

    Entity collection endpoints return a list of entities and an additional data structure with pagination links, such as
    "next", "prev", "first", and "last". The OSF API limits all entity collection responses to a maximum of 10 entities.
    The response object has two keys:

    + `data`

    `data` is an array of entities that match the query.  Each entity in the array is the same representation that is
    returned from that entity's `self` link, meaning that refetching the entity is unnecessary.

    + `links`

    `links` contains pagination information, including links to the previous, next, first, and last pages of results.
    The meta key contains the total number of entities available, as well as the current number of results displayed per
    page.  If there are only enough results to fill one page, the `first`, `last`, `prev`, and `next` values will be
    null.

    ###Errors

    When a request fails for whatever reason, the GakuNin RDM API will return an appropriate HTTP error code and include a
    descriptive error in the body of the response.  The response body will be an object with a key, `errors`, pointing
    to an array of error objects.  Generally, these error objects will consist of a `detail` key with a detailed error
    message and a `source` object that may contain a field `pointer` that is a [JSON
    Pointer](https://tools.ietf.org/html/rfc6901) to the error-causing attribute. The `error` objects may include
    additional information in accordance with the [JSON-API error spec](http://jsonapi.org/format/1.0/#error-objects).

    ####Example: Error response from an incorrect create node request

        {
          "errors": [
            {
              "source": {
                "pointer": "/data/attributes/category"
              },
              "detail": "This field is required."
            },
            {
              "source": {
                "pointer": "/data/type"
              },
              "detail": "This field may not be null."
            },
            {
              "source": {
                "pointer": "/data/attributes/title"
              },
              "detail": "This field is required."
            }
          ]
        }

    ##OSF Enum Fields

    Some entities in the GakuNin RDM API have fields that only take a restricted set of values.  Those fields are listed here
    for reference.  Fuller descriptions are available on the relevant entity pages.

    ###OSF Node Categories

        value                 description
        ==========================================
        project               Project
        hypothesis            Hypothesis
        methods and measures  Methods and Measures
        procedure             Procedure
        instrumentation       Instrumentation
        data                  Data
        analysis              Analysis
        communication         Communication
        other                 Other

    ###OSF Node Permission keys

        value        description
        ==========================================
        read         Read-only access
        write        Write access (make changes, cannot delete)
        admin        Admin access (full write, create, delete, contributor add)

    ###Storage Providers

    Valid storage providers are:

        value        description
        ==========================================
        bitbucket    Bitbucket
        box          Box.com
        dataverse    Dataverse
        dropbox      Dropbox
        figshare     figshare
        github       GitHub
        gitlab       GitLab
        googledrive  Google Drive
        onedrive     Microsoft OneDrive
        osfstorage   OSF Storage
        s3           Amazon S3

    """
    if request.user and not request.user.is_anonymous:
        user = request.user
        current_user = UserSerializer(user, context={'request': request}).data
    else:
        current_user = None
    kwargs = request.parser_context['kwargs']
    return_val = {
        'meta': {
            'message': 'Welcome to the GakuNin RDM API.',
            'version': request.version,
            'current_user': current_user,
        },
        'links': {
            'nodes': utils.absolute_reverse('nodes:node-list', kwargs=kwargs),
            'users': utils.absolute_reverse('users:user-list', kwargs=kwargs),
            'collections': utils.absolute_reverse('collections:collection-list', kwargs=kwargs),
            'registrations': utils.absolute_reverse('registrations:registration-list', kwargs=kwargs),
            'institutions': utils.absolute_reverse('institutions:institution-list', kwargs=kwargs),
            'licenses': utils.absolute_reverse('licenses:license-list', kwargs=kwargs),
            'metaschemas': utils.absolute_reverse('metaschemas:metaschema-list', kwargs=kwargs),
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

        return self.get_node().linked_nodes.filter(is_deleted=False).exclude(type='osf.collection').can_view(user=auth.user, private_link=auth.private_link).order_by('-modified')


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
                file_obj = base_class.objects.get(node=node, _path='/' + attrs['path'].lstrip('/'))
            except base_class.DoesNotExist:
                # create method on BaseFileNode appends provider, bulk_create bypasses this step so it is added here
                file_obj = base_class(node=node, _path='/' + attrs['path'].lstrip('/'), provider=base_class._provider)
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

    def get_file_object(self, node, path, provider, check_object_permissions=True):
        obj = get_file_object(node=node, path=path, provider=provider, request=self.request)
        if provider == 'osfstorage':
            if check_object_permissions:
                self.check_object_permissions(self.request, obj)
        return obj

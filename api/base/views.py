import weakref
from django.http import JsonResponse
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import generics
# from rest_framework.serializers
from rest_framework.mixins import ListModelMixin

from api.users.serializers import UserSerializer

from website import settings
from django.conf import settings as django_settings
from .utils import absolute_reverse, is_truthy

from .requests import EmbeddedRequest


CACHE = weakref.WeakKeyDictionary()


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
            v, view_args, view_kwargs = field.resolve(item, field_name)
            if not v:
                return None
            if isinstance(self.request._request, EmbeddedRequest):
                request = self.request._request
            else:
                request = EmbeddedRequest(self.request)

            view_kwargs.update({
                'request': request,
                'is_embedded': True
            })

            # Setup a view ourselves to avoid all the junk DRF throws in
            # v is a function that hides everything v.cls is the actual view class
            view = v.cls()
            view.args = view_args
            view.kwargs = view_kwargs
            view.request = request
            view.request.parser_context['kwargs'] = view_kwargs
            view.format_kwarg = view.get_format_suffix(**view_kwargs)

            _cache_key = (v.cls, field_name, view.get_serializer_class(), item)
            if _cache_key in CACHE.setdefault(self.request._request, {}):
                # We already have the result for this embed, return it
                return CACHE[self.request._request][_cache_key]

            # Cache serializers. to_representation of a serializer should NOT augment it's fields so resetting the context
            # should be sufficient for reuse
            if not view.get_serializer_class() in CACHE.setdefault(self.request._request, {}):
                CACHE[self.request._request][view.get_serializer_class()] = view.get_serializer_class()(many=isinstance(view, ListModelMixin))
            ser = CACHE[self.request._request][view.get_serializer_class()]

            try:
                ser._context = view.get_serializer_context()

                if not isinstance(view, ListModelMixin):
                    ret = ser.to_representation(view.get_object())
                else:
                    queryset = view.filter_queryset(view.get_queryset())
                    page = view.paginate_queryset(queryset)

                    ret = ser.to_representation(page or queryset)

                    if page is not None:
                        request.parser_context['view'] = view
                        request.parser_context['kwargs'].pop('request')
                        view.paginator.request = request
                        ret = view.paginator.get_paginated_response(ret).data
            except Exception as e:
                ret = view.handle_exception(e).data

            # Allow request to be gc'd
            ser._context = None

            # Cache our final result
            CACHE[self.request._request][_cache_key] = ret

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
            embeds = self.request.query_params.getlist('embed')

        fields_check = self.serializer_class._declared_fields.copy()

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
                is_truthy(self.request.query_params.get('esi', django_settings.ENABLE_ESI)) and
                self.request.accepted_renderer.media_type in django_settings.ESI_MEDIA_TYPES
            ),
            'embed': embeds_partials,
            'envelope': self.request.query_params.get('envelope', 'data'),
        })
        return context

@api_view(('GET',))
def root(request, format=None):
    """Welcome to the V2 Open Science Framework API. With this API you can access users, projects, components, logs, and files
    from the [Open Science Framework](https://osf.io/). The Open Science Framework (OSF) is a free, open-source service
    maintained by the [Center for Open Science](http://cos.io/).

    The OSF serves as a repository and archive for study designs, materials, data, manuscripts, or anything else
    associated with your research during the research process. Every project and file on the OSF has a permanent unique
    identifier, and every registration (a permanent, time-stamped version of your projects and files) can be assigned a
    DOI/ARK. You can use the OSF to measure your impact by monitoring the traffic to projects and files you make
    public. With the OSF you have full control of what parts of your research are public and what remains private.

    Beta notice: This API is currently a beta service.  You are encouraged to use the API and will receive support
    when doing so, however, while the API remains in beta status, it may change without notice as a result of
    product updates. The temporary beta status of the API will remain in place while it matures. In a future
    release, the beta status will be removed, at which point we will provide details on how long we will support
    the API V2 and under what circumstances it might change.

    #General API Usage

    The OSF API generally conforms to the [JSON-API v1.0 spec](http://jsonapi.org/format/1.0/).  Where exceptions
    exist, they will be noted.  Each endpoint will have its own documentation, but there are some general principles.

    ##Requests

    ###Canonical URLs

    All canonical URLs have trailing slashes.  A request to an endpoint without a trailing slash will result in a 301
    redirect to the canonical URL.  There are some exceptions when working with the Files API, so if a URL in a response
    does not have a slash, do not append one.

    ###Plurals

    Endpoints are always pluralized.  `/users/`, not `/user/`, `/nodes/`, not `/node/`.

    ###Common Actions

    Every endpoint in the OSF API responds to `GET`, `HEAD`, and `OPTION` requests.  You must have adequate permissions
    to interact with the endpoint.  Unauthorized use will result in 401 Unauthorized or 403 Forbidden responses.  Use
    `HEAD` to probe an endpoint and make sure your headers are well-formed.  `GET` will return a representation of the
    entity or entity collection referenced by the endpoint.  An `OPTIONS` request will return a JSON object that describes the
    endpoint, including the name, a description, the acceptable request formats, the allowed response formats, and any
    actions available via the endpoint.

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
    entity.  If you attempt to set an attribute that does not permit updates (such as a `date_created` timestamp), the
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

    When a request fails for whatever reason, the OSF API will return an appropriate HTTP error code and include a
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

    Some entities in the OSF API have fields that only take a restricted set of values.  Those fields are listed here
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
        box          Box.com
        cloudfiles   Rackspace Cloud Files
        dataverse    Dataverse
        dropbox      Dropbox
        figshare     figshare
        github       GitHub
        googledrive  Google Drive
        osfstorage   OSF Storage
        s3           Amazon S3

    """
    if request.user and not request.user.is_anonymous():
        user = request.user
        current_user = UserSerializer(user, context={'request': request}).data
    else:
        current_user = None

    return_val = {
        'meta': {
            'message': 'Welcome to the OSF API.',
            'version': request.version,
            'current_user': current_user,
        },
        'links': {
            'nodes': absolute_reverse('nodes:node-list'),
            'users': absolute_reverse('users:user-list'),
            'collections': absolute_reverse('collections:collection-list'),
            'registrations': absolute_reverse('registrations:registration-list'),
            'institutions': absolute_reverse('institutions:institution-list'),
            'licenses': absolute_reverse('licenses:license-list'),
        }
    }
    if settings.DEV_MODE:
        return_val['links']['metaschemas'] = absolute_reverse('metaschemas:metaschema-list')

    return Response(return_val)


def error_404(request, format=None, *args, **kwargs):
    return JsonResponse(
        {'errors': [{'detail': 'Not found.'}]},
        status=404,
        content_type='application/vnd.api+json; application/json'
    )

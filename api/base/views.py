from rest_framework.decorators import api_view
from rest_framework.response import Response

from .utils import absolute_reverse
from api.users.serializers import UserSerializer

@api_view(('GET',))
def root(request, format=None):
    """Welcome to the V2 Open Science Framework API. With this API you can programatically access users,
    projects, components, and files from the [Open Science Framework](https://osf.io/). The Open Science
    Framework (OSF) is a free, open-source service maintained by the [Center for Open Science](http://cos.io/).

    The OSF stores, documents, and archives study designs, materials, data, manuscripts, or anything else associated
    with your research during the research process. Every project and file on the OSF has a permanent unique
    identifier, and every registration (a permanent, time-stamped version of your projects and files) can be assigned
    a DOI/ARK. You can use the OSF to measure your impact by monitoring the traffic to projects and files you make
    public. With the OSF you have full control of what parts of your research are public and what remains private.

    Beta notice: This API is currently a beta service.  You are encouraged to use the API and will receive support
    when doing so, however, while the API remains in beta status, it may change without notice as a result of
    product updates. The temporary beta status of the API will remain in place while it matures. In a future
    release, the beta status will be removed, at which point we will provide details on how long we will support
    the API V2 and under what circumstances it might change.

    #General API Usage

    The OSF API generally conforms to the [JSON-API v1.0 spec](http://jsonapi.org/format/1.0/).  Where exceptions
    exists, they will be noted.  Each endpoint will have its own documentation, but there are some general principles.

    ##Requests

    ###Canonical URLs

    All canonical URLs have trailing slashes.  A request to an endpoint without a trailing slash will result in a
    301 redirect to the canonical URL.

    ###Plurals

    Endpoints are always pluralized.  `/users/`, not `/user/`, `/nodes/`, not `/node/`.

    ###Common Actions

    Every endpoint in the OSF API responds to `GET`, `HEAD`, and `OPTION` requests.  You must have adequate
    permissions to interact with the endpoint.  Unauthorized use will result in 401 Aunuthorized or 403 Forbidden
    responses.  Use `HEAD` to probe an endpoint and make sure your headers are well-formed.  `GET` will return a
    JSON representation of the entity or collection referenced by the endpoint.  An `OPTIONS` request will return a
    JSON object that describes the endpoint, including the name, a description, the acceptable request formats, the
    allowed response formats, and any actions available via the endpoint.

    ###Filtering

    Collections can be filtered by adding a query parameter in the form:

        filter[<fieldname>]=<matching information>
    For example, if you were trying to find [Lise Meitner](http://en.wikipedia.org/wiki/Lise_Meitner):

        /users/?filter[fullname]=meitn
    You can filter on multiple fields, or the same field in different ways, by &-ing the query parameters together.

        /users/?filter[fullname]=lise&filter[family_name]=mei

    ###Pagination

    All collection endpoints respond to the `page` query parameter behavior as described in the [JSON-API pagination
    spec](http://jsonapi.org/format/1.0/#crud).

    ###Formatting POST/PUT/PATCH request bodies

    The OSF API follows the JSON-API spec for (create and update requests)[http://jsonapi.org/format/#crud].  This means
    all request bodies must be wrapped with some metadata.  Each request body must be an object with a `data` key
    containing at least a `type` member.  The value of the `type` member must agree with the `type` of the entitys
    represented by the endpoint.  If not, a 409 Conflict will be returned.  The request should also contain an
    `attributes` member with an object containing the key-value pairs to be created/updated.  PUT/PATCH requests must
    also have an `id` key that matches the id part of the endpoint.  If the `id` key does not match the id path part, a
    409 Conflict error will be returned.

    ##Responses

    ###Entities

    An entity is a single resource that has been retreived from the API, usually from an endpoint with the entity's id
    as the final path part.  A successful response from an entity request will be a JSON object with a top level `data`
    key pointing to a sub-object with the following members:

    + `id`

    The identifier for the entity.  This MUST be included with [PUT and PATCH
    requests](#formatting-post-put-patch-request-bodies).

    + `type`

    The type identifier of this entity.  This MUST be included with [all create/update
    requests](#formatting-post-put-patch-request-bodies).

    + `attributes`

    The properties of the entity.  Names, descriptions, etc.

    + `relationships`

    Relationships are urls to other entities or collections that have a relationship to the entity. For example, the
    node entity provides a `contributors` relationship that points to the endpoint to retreive all contributors to that
    node.  It is reccommended to use these links rather than to id-filter of general collection endpoints.  They'll be
    faster, easier, and less error-prone.

    + `links`

    Links are urls to alternative representations of the entity or actions that may be performed on the entity.  Most
    entities will provide a `self` link that is the canonical endpoint for the entity where update and delete requests
    should be sent.  In-depth documentation of actions is available by navigating to the `self` link in the Browsable
    API.  Most entities will also provide an `html` link that directs to the entity's page on the [OSF](http://osf.io/).

    ###Collections

    Collection endpoints return a list of entities and an additional data structure with pagination links, such as
    "next", "prev", "first", and "last". The OSF API limits all collection responses to a maximum of 10 entities.  The
    response object has two keys:

    + `data`

    `data` is an array of entities that match the query.  Each entity in the array is the same representation that is
    returned from that entity's `self` link, meaning that refetching the entity is unnecessary.

    + `links`

    `links` contains pagination information, including links to the previous, next, first, and last pages of results.
    The meta key contains the total number of entities available, as well as the current number of results displayed per
    page.  If there are only enough results to fill one page, the `first`, `last`, `prev`, and `next` values will be
    null.

    ###PUT vs. PATCH

    For most endpoints that support updates via PUT requests, we also allow PATCH updates.  The only difference is that
    PUT requests require all mandatory attributes to be set, even if their value is unchanged.  PATCH requests may omit
    mandatory attributes, whose value will be unchaged.

    ###Attribute Validation

    Endpoints that allow creation or modification of entities generally limit updates to certain attributes of the
    entity.  If you attempt to set an attribute that does not permit updates (such as a `date_created` timestamp), the
    API will silently ignore that attribute.  This will not affect the response from the API: if the request would have
    succeeded without the updated attribute, it will still report as successful.  Likewise, if the request would have
    failed without the attribute update, the API will still report a failure.

    Typoed or non-existant attributes will behave the same as non-updatable attributes and be silently
    ignored. If a request is not working the way you expect, make sure to double check your spelling.

    ###Errors

    When a request fails for whatever reason, the OSF API will return an appropriate HTTP error code and include a
    descriptive error in the body of the response.  The response body will be an object with a key, `errors`, pointing
    to an array of error objects.  Generally, these error object will consist of a `detail` key with a detailed error
    message, but may include additional information in accordance with the [JSON-API error
    spec](http://jsonapi.org/format/1.0/#error-objects).

    ##OSF Enum Fields

    Some entities in the OSF API have fields that only take a restricted set of values.  Those fields are listed here
    for reference.  Fuller descriptions are available on the relevent entity pages.

    ###OSF Node Categories

        value                 description
        ------------------------------------------
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
        ------------------------------------------
        read         Read-only access
        write        Write access (make changes, cannot delete)
        admin        Admin access (full write, create, delete, contributor add)

    ###Storage Providers

    Valid storage providers are:

        value        description
        ------------------------------------------
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

    return Response({
        'meta': {
            'message': 'Welcome to the OSF API.',
            'version': request.version,
            'current_user': current_user,
        },
        'links': {
            'nodes': absolute_reverse('nodes:node-list'),
            'users': absolute_reverse('users:user-list'),
        }
    })

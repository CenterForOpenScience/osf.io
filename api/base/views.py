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

    ##General API Usage

    Each endpoint will have its own documentation, but there are some general principles.

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

        /users?filter[fullname]=meitn
    You can filter on multiple fields, or the same field in different ways, by &-ing the query parameters together.

        /users?filter[fullname]=lise&filter[family_name]=mei

    ###Links

    Responses will generally have associated links which are helpers to keep you from having to construct URLs in
    your code or by hand. If you know the route to a high-level resource, you can go to that route. For example:

        /nodes/<node_id>

    is a good route to create rather than going to /nodes/ and navigating by id filtering. However, if you are
    creating something that crawls the structure of a node going to the child node or gathering children,
    contributors, and similar related resources, then take the link from the object you\'re crawling rather than
    constructing the link yourself.

    In general, links include:

    1. "Related" links, which will give detailed information on individual items or a collection of related resources;
    2. "Self" links, which are used for general REST operations (POST, DELETE, and so on);
    3. Pagination links such as "next", "prev", "first", and "last". Pagination links are great for navigating long
    lists of information.

    Some routes may have extra rules for links, especially if those links work with external services. Collections
    may have counts with them to indicate how many items are in that collection.

    ###Formatting POST/PUT/PATCH requests

    The OSF API follows the JSON-API spec for [create and update requests](http://jsonapi.org/format/#crud).  This means
    all request bodies must be wrapped with some metadata.  Each request body must be an object with a `data` key
    containing at least a `type` member.  The value of the `type` member must agree with the `type` of the entitys
    represented by the endpoint.  If not, a 409 Conflict will be returned.  The request should also contain an
    `attributes` member with an object containing the key-value pairs to be created/updated.  PUT/PATCH requests must
    also have an `id` key that matches the id part of the endpoint.  If the `id` key does not match the id path part, a
    409 Conflict error will be returned.

    ###Attribute Validation

    Endpoints that allow creation or modification of entities generally limit updates to certain attributes of the
    entity.  If you attempt to set an attribute that does not permit updates (such as a `date_created` timestamp), the
    API will silently ignore that attribute.  This will not affect the response from the API: if the request would have
    succeeded without the updated attribute, it will still report as successful.  Likewise, if the request would have
    failed without the attribute update, the API will still report a failure.

    Typoed or non-existant attributes will behave the same as non-updatable attributes and be silently
    ignored. If a request is not working the way you expect, make sure to double check your spelling.

    ###PUT vs. PATCH

    For most endpoints that support updates via PUT requests, we also allow PATCH updates.  The only difference is that
    PUT requests require all mandatory attributes to be set, even if their value is unchanged.  PATCH requests may omit
    mandatory attributes, whose value will be unchaged.


    ###OSF Permission keys

    Valid OSF permission keys include "read", "write", and "admin".

    ###Storage Providers

    Valid storage providers are:

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

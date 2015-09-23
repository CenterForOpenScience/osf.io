from rest_framework import generics
from rest_framework import permissions as drf_permissions
from rest_framework.exceptions import NotAuthenticated
from django.contrib.auth.models import AnonymousUser

from modularodm import Q

from framework.auth.core import Auth
from framework.auth.oauth_scopes import CoreScopes

from website.models import User, Node

from api.base import permissions as base_permissions
from api.base.utils import get_object_or_error
from api.base.filters import ODMFilterMixin
from api.nodes.serializers import NodeSerializer

from .serializers import UserSerializer
from .permissions import ReadOnlyOrCurrentUser


class UserMixin(object):
    """Mixin with convenience methods for retrieving the current node based on the
    current URL. By default, fetches the user based on the user_id kwarg.
    """

    serializer_class = UserSerializer
    user_lookup_url_kwarg = 'user_id'

    def get_user(self, check_permissions=True):
        key = self.kwargs[self.user_lookup_url_kwarg]
        current_user = self.request.user

        if key == 'me':
            if isinstance(current_user, AnonymousUser):
                raise NotAuthenticated
            else:
                return self.request.user

        obj = get_object_or_error(User, key, 'user')
        if check_permissions:
            # May raise a permission denied
            self.check_object_permissions(self.request, obj)
        return obj


class UserList(generics.ListAPIView, ODMFilterMixin):
    """List of users registered on the OSF. *Read-only*.

    Paginated list of users ordered by the date they registered.  Each resource contains the full representation of the
    user, meaning a re-fetch is not necessary.

    The subroute [`/me/`](me/) is a special link that always points to the currently logged-in user.

    ##User Attributes

    **TODO: import from UserDetail**

    ##Links

    See the [JSON-API spec regarding pagination](http://jsonapi.org/format/#fetching-pagination).

    ##Actions

    *None*.

    ##Query Params

    + `page=<Int>` -- page number of results to view, default 1

    + `filter[<fieldname>]=<Str>` -- fields and values to filter the search results on.

    Users may be filtered by their `id`, `full_name`, `given_name`, `middle_names`, or `family_name`.

    """
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.USERS_READ]
    required_write_scopes = [CoreScopes.USERS_WRITE]

    serializer_class = UserSerializer

    ordering = ('-date_registered')

    # overrides ODMFilterMixin
    def get_default_odm_query(self):
        return (
            Q('is_registered', 'eq', True) &
            Q('is_merged', 'ne', True) &
            Q('date_disabled', 'eq', None)
        )

    # overrides ListAPIView
    def get_queryset(self):
        # TODO: sort
        query = self.get_query_from_request()
        return User.find(query)


class UserDetail(generics.RetrieveUpdateAPIView, UserMixin):
    """Details about a specific user. *Writeable*.

    If `me` is given as the id, the record of the currently logged-in user will be returned.

    ##Attributes

        name               type               description
        ----------------------------------------------------------------------------------------
        full_name          string             full name of the user
        given_name         string             given name of the user for bibliographic citations
        middle_names       string             middle name of user for bibliographic citations
        family_name        string             family name of user for bibliographic citations
        suffix             string             suffix of user's name for bibliographic citations
        date_registered    iso8601 timestamp  timestamp when the user's account was created
        profile_image_url  url                url to the user's profile image (gravatar)

    ##Relationships

    ###Nodes

    A list of all nodes the user has contributed to.  If the user id in the path is the same as the logged-in user, all
    nodes will be visible.  Otherwise, you will only be able to see the other user's publicly-visible nodes.

    ##Links

        self:  the canonical api endpoint of this user
        html:  this user's page on the OSF website

    ##Actions

    ###Update

        Method:        PUT / PATCH
        URL:           links.self
        Query Params:  <none>
        Body (JSON):   {
                         "full_name":    "<mandatory>",
                         "given_name":   "<optional>",
                         "middle_names": "<optional>",
                         "family_name":  "<optional>",
                         "suffix":       "<optional">
                       }
        Success:       200 OK + node representation

    To update your user profile, issue a PUT request to either the canonical URL of your user resource (as given in
    `links.self`) or to `/users/me/`.  Only the `full_name` attribute is required.  Unlike at signup, the given, middle,
    and family names will not be inferred from the `full_name`.  Currently, only `full_name`, `given_name`,
    `middle_names`, `family_name`, and `suffix` are updateable.

    A PATCH request issued to this endpoint will behave the same as a PUT request, but does not require `full_name` to
    be set.

    ##Query Params

    *None*.

    """
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        ReadOnlyOrCurrentUser,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.USERS_READ]
    required_write_scopes = [CoreScopes.USERS_WRITE]

    serializer_class = UserSerializer

    # overrides RetrieveAPIView
    def get_object(self):
        return self.get_user()

    # overrides RetrieveUpdateAPIView
    def get_serializer_context(self):
        # Serializer needs the request in order to make an update to privacy
        return {'request': self.request}


class UserNodes(generics.ListAPIView, UserMixin, ODMFilterMixin):
    """List of nodes that the user contributes to. *Read-only*.

    Paginated list of nodes that the user contributes to.  Each resource contains the full representation of the node,
    meaning a re-fetch is not necessary. If the user id in the path is the same as the logged-in user, all nodes will be
    visible.  Otherwise, you will only be able to see the other user's publicly-visible nodes.  The special user id `me`
    can be used to represent the currently logged-in user.

    ##Node Attributes

    **TODO: import from NodeDetail**

    ##Links

    See the [JSON-API spec regarding pagination](http://jsonapi.org/format/#fetching-pagination).

    ##Actions

    *None*.

    ##Query Params

    + `page=<Int>` -- page number of results to view, default 1

    + `filter[<fieldname>]=<Str>` -- fields and values to filter the search results on.

    **TODO: import from NodeList**

    """
    permission_classes = (
        drf_permissions.IsAuthenticatedOrReadOnly,
        base_permissions.TokenHasScope,
    )

    required_read_scopes = [CoreScopes.USERS_READ, CoreScopes.NODE_BASE_READ]
    required_write_scopes = [CoreScopes.USERS_WRITE, CoreScopes.NODE_BASE_WRITE]

    serializer_class = NodeSerializer

    # overrides ODMFilterMixin
    def get_default_odm_query(self):
        user = self.get_user()
        return (
            Q('contributors', 'eq', user) &
            Q('is_folder', 'ne', True) &
            Q('is_deleted', 'ne', True)
        )

    # overrides ListAPIView
    def get_queryset(self):
        current_user = self.request.user
        if current_user.is_anonymous():
            auth = Auth(None)
        else:
            auth = Auth(current_user)
        query = self.get_query_from_request()
        raw_nodes = Node.find(self.get_default_odm_query() & query)
        nodes = [each for each in raw_nodes if each.is_public or each.can_view(auth)]
        return nodes

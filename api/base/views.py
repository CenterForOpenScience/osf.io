from rest_framework.decorators import api_view
from rest_framework.response import Response

from .utils import absolute_reverse
from api.users.serializers import UserSerializer

@api_view(('GET',))
def root(request, format=None):
    """
        Welcome to the V2 Open Science Framework API. With this API you can programatically access users,
        projects, components, and files from the [Open Science Framework](https://osf.io/). The Open Science
        Framework is a website that integrates with the scientist's daily workflow. OSF helps document and archive
        study designs, materials, and data. OSF facilitates sharing of materials and data within a research group
        or between groups. OSF also facilitates transparency of research and provides a network design that details
        and credits individual contributions for all aspects of the research process.

        NOTE: This API is currently in beta. The beta period should be fairly short, but until then, details about
        the api could change. Once this notice disappears, it will be replaced with a description of how long we will
        support the current api and under what circumstances it might change.
        ##General API Usage
        Each endpoint will have its own documentation, but there are some general things that should work pretty much everywhere.
        ###Filtering
        Collections can be filtered by adding a query parameter in the form:

            filter[<fieldname>]=<matching information>
        For example, if you were trying to find [Lise Meitner](http://en.wikipedia.org/wiki/Lise_Meitner):

            /users?filter[fullname]=meitn
        You can filter on multiple fields, or the same field in different ways, by &-ing the query parameters together.

            /users?filter[fullname]=lise&filter[family_name]=mei
        ###Links
        Responses will generally have associated links. These are helpers to keep you from having to construct
        URLs in your code or by hand. If you know the route to a high-level resource, then feel free to just go to that
        route. For example, going to:

            /nodes/<node_id>
        is a perfectly good route to create rather than going to /nodes/ and navigating from there by filtering by id
        (which would be ridiculous). However, if you are creating something that crawls the structure of a node
        going to child node or gathering children, contributors, and similar related resources, then grab the link from
        the object you\'re crawling rather than constructing the link yourself.

        In general, links include:

        1. "Related" links, which will give you detail information on individual items or a collection of related resources;
        2. "Self" links, which is what you use for general REST operations (POST, DELETE, and so on);
        3. Pagination links such as "next", "prev", "first", and "last". These are great for navigating long lists of information.

        Some routes may have extra rules for links, especially if those links work with external services. Collections
        may have counts with them to indicate how many items are in that collection.

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

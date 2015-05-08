from rest_framework.decorators import api_view
from rest_framework.response import Response

from .utils import absolute_reverse
from api.users.serializers import UserSerializer

@api_view(('GET',))
def root(request, format=None):
    """
    Welcome to the V2 Open Science Framework API.

    Each endpoint will have its own documentation, but there are some general things that should work
    pretty much everywhere.

    <h2>Filtering</h2>

    Collections can be filtered by adding a query parameter in the form:

    <pre>filter[&lt;fieldname&gt;]=&lt;matching information&gt;</pre>

    For example, if you were trying to find <a href="http://en.wikipedia.org/wiki/Lise_Meitner">
    Lise Metiner</a>:

    <pre>/users?filter[fullname]=meitn</pre>

    You can filter on multiple fields, or the same field in different ways, by &-ing the query parameters together.

    <pre>/users?filter[fullname]=lise&family_name=mei</pre>

    <h2>Links</h2>
    Responses will generally have associated links. These are helpers to keep you from having to construct
    URLs in your code or by hand. If you know the route to a high-level resource, then feel free to just go to that
    route. For example, going to:

    <pre>/nodes/<node_id></pre>

    is a perfectly good route to create rather than going to /nodes/ and navigating from there by filtering by id
     (which would be ridiculous). However, if you are creating something that crawls the structure of a node
     going to child node or gathering children, contributors, and similar related resources, then grab the link from
     the object you're crawling rather than constructing the link yourself.

    In general, links include:
    <ol>
    <li>'related' links, which will give you detail information on individual items or a collection
    of related resources;</li>
    <li>'self' links, which is what you use for general REST operations (POST, DELETE, and so on);</li>
    <li> Pagination links such as 'next', 'prev', 'first', and 'last'. These are great for navigating long lists
    of information.</li>
    </ol>
    Some routes may have extra rules for links, especially if those links work with external services.
    """
    if request.user and not request.user.is_anonymous():
        user = request.user
        current_user = UserSerializer(user).data
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
